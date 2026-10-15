import {activityCategories} from "./activity-categories.js";
import {registerUnpaidRenewal} from "./manual-pending-renewal";
import {deletePendingRenewal,savePendingUnit,confirmRenewalPayment,undoRenewalPayment} from "./pending-renewals";
import {reviewInventory} from "./review-inventory";
import {recordTransfer,undoTransfer} from "./transfers";
import {validateRenewCounts} from './renewal-kpi.js';
import { exitCategories, vacancyDate } from "./targets.js";
import { deleteUserAccount } from "./delete-user";
import { removeActivity } from "./remove-activity";
import { parseLease } from "./lease.js";
import { removeImport, sourceFiles } from "./import-actions";

import {
  pricingUpdate,
  priceSnapshot,
  frozenAmounts,
} from "./pricing.js";

import {
  initializeApp,
  deleteApp
} from "firebase/app";

import {
  getAuth,
  createUserWithEmailAndPassword,
  connectAuthEmulator
} from "firebase/auth";

import {
  doc,
  collection,
  getDoc, getDocs,
  runTransaction,
  writeBatch,
  serverTimestamp,
  getFirestore,
  connectFirestoreEmulator,
  deleteField
} from "firebase/firestore";

import {
  auth,
  db,
  config,
  loginEmail
} from "./firebase";

import {
  normalizeUnits,
  inventoryStats,
  validDate,
  taipeiDate
} from "./domain.js";

const time = () => serverTimestamp();

const branch = (id: string) => {
  if (!id || id.includes("/")) {
    throw new Error("據點不合法");
  }

  return doc(db, "branches", id);
};

const uid = () => {
  if (!auth.currentUser) {
    throw new Error("請先登入");
  }

  return auth.currentUser.uid;
};

export async function execute(
  name: string,
  data: any
): Promise<any> {
  const me = uid();

  switch (name) {
    case "registerProfile": {
      if (auth.currentUser?.email !== loginEmail(data.username)) throw new Error("帳號不符");
      const ref = doc(db,"users",me), person = doc(db,"workPeople",me);
      await runTransaction(db,async transaction=>{
        const existing = await transaction.get(ref), directory = await transaction.get(person);
        const username = existing.exists()?existing.data().username:data.username;
        if(!existing.exists()) transaction.set(ref,{username,role:"pending",branchIds:[],mustChangePassword:false,createdAt:time()});
        if(!directory.exists()||directory.data().username!==username)transaction.set(person,{username});
      });
      return {};
    }
    case "passwordChanged": {
      const ref = doc(db, "users", me);
      const batch = writeBatch(db);

      batch.update(ref, {
        mustChangePassword: false
      });

      await batch.commit();

      return {};
    }

    case "deleteUser": { return deleteUserAccount(data); }
    case "manageUser": {
      if (data.action === "create") {
        const app = initializeApp(
          config,
          `create-user-${crypto.randomUUID()}`
        );

        try {
          const otherAuth = getAuth(app);
          const otherDb = getFirestore(app);

          if (
            import.meta.env.VITE_USE_EMULATORS === "true"
          ) {
            connectAuthEmulator(
              otherAuth,
              "http://127.0.0.1:9099",
              { disableWarnings: true }
            );

            connectFirestoreEmulator(
              otherDb,
              "127.0.0.1",
              8080
            );
          }

          const user =
            await createUserWithEmailAndPassword(
              otherAuth,
              loginEmail(data.username),
              data.password
            );

          const batch = writeBatch(otherDb);

          batch.set(
            doc(otherDb, "users", user.user.uid),
            {
              username: data.username,
              role: "pending",
              branchIds: [],
              mustChangePassword: true,
              createdAt: time()
            }
          );

          batch.set(doc(otherDb, "workPeople", user.user.uid), {username: data.username});
          await batch.commit();
        } finally {
          await deleteApp(app);
        }

        return {};
      }

      const ref = doc(db, "users", data.uid);
      const batch = writeBatch(db);

      batch.update(ref, {
        role: data.role,
        branchIds: [...new Set(data.branchIds)],
        updatedBy: me,
        updatedAt: time()
      });

      await batch.commit();

      return {};
    }

    case "saveBranch": {
      const ref = data.id
        ? branch(data.id)
        : doc(collection(db, "branches"));

      if (!String(data.name).trim()) {
        throw new Error("請填寫據點名稱");
      }

      const openingMonth=String(data.openingMonth||"");
      if ("openingMonth" in data && openingMonth && !/^20\d{2}-(0[1-9]|1[0-2])$/.test(openingMonth)) throw new Error("開幕月份不合法");
      await runTransaction(db, async (transaction) => {
        const old = await transaction.get(ref);

        if (old.data()?.importing) {
          throw new Error("據點正在匯入");
        }

        transaction.set(
          ref,
          {
            name: String(data.name).trim(),
            ...("openingMonth" in data ? {openingMonth:openingMonth||null} : {}),
            ...(!old.exists()
              ? {
                  total: 0,
                  rented: 0,
                  vacant: 0,
                  revision: 0
                }
              : {}),
            updatedAt: time()
          },
          { merge: true }
        );
      });

      return { id: ref.id };
    }

    case "saveActivity": {
      if(data.category && !activityCategories.includes(data.category))
        throw new Error("請選擇有效的活動分類");
      const ref = data.id
        ? doc(
            db,
            "branches",
            data.branchId,
            "activities",
            data.id
          )
        : doc(
            collection(
              db,
              "branches",
              data.branchId,
              "activities"
            )
          );

      if (
        !/^\d{4}-(0[1-9]|1[0-2])$/.test(
          data.month
        ) ||
        !String(data.name || "").trim()
      ) {
        throw new Error("活動月份與名稱必填");
      }

      const batch = writeBatch(db);

      batch.set(
        ref,
        {
          month: data.month,
          ...(data.category?{category:data.category}:{}),name: String(data.name).trim(),
          description: String(
            data.description || ""
          ),
          archived: !!data.remove,
          updatedBy: me,
          updatedAt: time()
        },
        { merge: true }
      );

      await batch.commit();

      return {};
    }

    case "recordTransfer": return recordTransfer(data);
    case "undoTransfer": return undoTransfer(data);
    case "recordEvent": {
      if(data.unpaid === "on")return registerUnpaidRenewal(data);
      const {
        branchId,
        code,
        type,
        date,
        activityIds = []
      } = data;

      if (
        !["new", "renew", "exit"].includes(type) ||
        !validDate(date) ||
        date > taipeiDate()
      ) {
        throw new Error("異動日期或類型不合法");
      }

      const branchDoc = branch(branchId);

      const unitDoc = doc(
        db,
        "branches",
        branchId,
        "units",
        code
      );

      const eventDoc = doc(
        collection(
          db,
          "branches",
          branchId,
          "events"
        )
      );

      const eventMonthDoc = doc(
        db,
        "branches",
        branchId,
        "months",
        date.slice(0, 7)
      );

      const currentMonthDoc = doc(
        db,
        "branches",
        branchId,
        "months",
        taipeiDate().slice(0, 7)
      );

      await runTransaction(db, async (transaction) => {
        const [
          branchSnapshot,
          unitSnapshot,
          monthSnapshot,
          currentMonthSnapshot
        ] = await Promise.all([
          transaction.get(branchDoc),
          transaction.get(unitDoc),
          transaction.get(eventMonthDoc),
          transaction.get(currentMonthDoc)
        ]);

        if (
          !branchSnapshot.exists() ||
          !unitSnapshot.exists()
        ) {
          throw new Error("據點或倉位不存在");
        }

        const unit = unitSnapshot.data();
        const branchData = branchSnapshot.data();

        if (branchData.importing) {
          throw new Error("據點正在匯入");
        }

        if (unit.missing) {
          throw new Error(
            "消失的倉位請重新匯入確認"
          );
        }

        if (
          monthSnapshot.data()?.source === "import"
        ) {
          throw new Error(
            "該月已有歷史 KPI，請先移除該月統計"
          );
        }

        if (
          (
            type === "new" &&
            unit.status !== "vacant"
          ) ||
          (
            type !== "new" &&
            unit.status !== "rented"
          )
        ) {
          throw new Error(
            "狀態已變更，請重新整理"
          );
        }

        if (
          unit.lastEventDate &&
          date < unit.lastEventDate
        ) {
          throw new Error(
            "日期不得早於該倉位上一筆異動"
          );
        }

        const activities = [];

        for (
          const id of
          [...new Set(activityIds)] as string[]
        ) {
          const activitySnapshot =
            await transaction.get(
              doc(
                db,
                "branches",
                branchId,
                "activities",
                id
              )
            );

          if (
            !activitySnapshot.exists() ||
            activitySnapshot.data().archived ||
            activitySnapshot.data().month !==
              date.slice(0, 7)
          ) {
            throw new Error(
              "活動不適用於此月份"
            );
          }

          activities.push({
            id,
            name: activitySnapshot.data().name
          });
        }

        if (
          type === "exit" &&
          activities.length
        ) {
          throw new Error("退租不能使用優惠");
        }

        const exitReason = type === "exit" && typeof data.exitReason === "string"
          ? data.exitReason.trim() : "";
        if (type === "exit" && (!exitReason || exitReason.length > 500))
          throw new Error("退租原因請填寫 1～500 字，不能只有空白");
        const lease = parseLease(type === "exit" ? "" : data.leasePeriod);
        if (type !== "exit" && !lease.leasePeriod) throw new Error("承租與續約必須填寫租期");
        const exitCategory = type === "exit" ? String(data.exitCategory || "") : "";
        if (type === "exit" && !exitCategories.includes(exitCategory))
          throw new Error("請選擇退租原因分類");
        const previousLease = {
          vacantSince: unit.vacantSince || null,
          leasePeriod: unit.leasePeriod || "",
          leaseStart: unit.leaseStart || null,
          leaseEnd: unit.leaseEnd || null,
        };
        const delta =
          type === "new"
            ? 1
            : type === "exit"
              ? -1
              : 0;

        const rented =
          branchData.rented + delta;

        const vacant =
          branchData.vacant - delta;

        transaction.update(unitDoc, {
          ...lease,
          vacantSince: type === "exit" ? date : null,
          status:
            type === "exit"
              ? "vacant"
              : "rented",
          lastEventDate: date,
          lastEventId: eventDoc.id,
          updatedAt: time()
        });

        transaction.update(branchDoc, {
          rented,
          vacant,
          revision: branchData.revision + 1,
          updatedAt: time()
        });

        transaction.set(eventDoc, {
          code,
          type,
          date,
          month: date.slice(0, 7),
          activities,
          exitReason, exitCategory,
          priceSnapshot: priceSnapshot(unit, date),
          unitSnapshot: {
            dimensions: unit.dimensions,
            volume: unit.volume,
            price: priceSnapshot(unit, date).price,
            note: unit.note,
            ...lease,
          },
          previousLease,
          previousEventDate:
            unit.lastEventDate || null,
          previousEventId:
            unit.lastEventId || null,
          createdBy: me,
          createdAt: time(),
          voided: false
        });

        transaction.set(
          eventMonthDoc,
          {
            source: "live",
            [type]:
              (
                monthSnapshot.data()?.[type] ||
                0
              ) + 1,
            updatedAt: time()
          },
          { merge: true }
        );

        if (
          currentMonthSnapshot.data()?.source !==
          "import"
        ) {
          transaction.set(
            currentMonthDoc,
            {
              source: "live",
              total: branchData.total,
              rented,
              snapshotDate: taipeiDate(),
              updatedAt: time()
            },
            { merge: true }
          );
        }
      });

      return {};
    }

    case "removeActivity": {
      return removeActivity(data);
    }

    case "voidEvent": {
      const check=await getDoc(doc(db,"branches",data.branchId,"events",data.eventId));
      if(check.data()?.paymentConfirmation)return undoRenewalPayment(data);
      if(["transferOut","transferIn"].includes(check.data()?.type))return undoTransfer(data);
      const b = branch(data.branchId),
        e = doc(db, "branches", data.branchId, "events", data.eventId);

      await runTransaction(db, async (t) => {
        const [bs, es, actor] = await Promise.all([
          t.get(b),
          t.get(e),
          t.get(doc(db, "users", me)),
        ]);

        if (!es.exists() || es.data().voided || bs.data()?.importing)
          throw new Error("異動不存在、已撤銷或據點正在匯入");

        const event = es.data(),
          u = doc(db, "branches", data.branchId, "units", event.code),
          m = doc(db, "branches", data.branchId, "months", event.month),
          n = doc(
            db,
            "branches",
            data.branchId,
            "months",
            taipeiDate().slice(0, 7),
          );

        const [us, ms, ns] = await Promise.all([
          t.get(u), t.get(m), t.get(n),
        ]);

        const isAdmin = actor.data()?.role === "admin";

        const last =
          us.exists() &&
          us.data().lastEventId === data.eventId &&
          !us.data().missing &&
          !us.data().archived;

        const count = ms.data()?.[event.type];

        const counted =
          ms.data()?.source === "live" &&
          Number.isInteger(count) &&
          count > 0;

        const safeState =
          event.type === "new"
            ? bs.data()!.rented > 0
            : event.type === "exit"
              ? bs.data()!.vacant > 0
              : true;

        if (isAdmin && (!last || !counted || !safeState)) {
          t.update(e, {
            voided: true,
            voidedBy: me,
            voidedAt: time(),
            voidMode: "history",
          });

          if (counted) {
            t.set(
              m,
              { [event.type]: count - 1 },
              { merge: true },
            );
          }

          t.update(b, {
            revision: bs.data()!.revision + 1,
            updatedAt: time(),
          });

          return;
        }

        if (!last)
          throw new Error("只能撤銷該倉位最後一筆異動");

        if (ms.data()?.source === "import")
          throw new Error("該月已匯入歷史 KPI");

        if (
          !Number.isInteger(ms.data()?.[event.type]) ||
          ms.data()![event.type] < 1
        )
          throw new Error(
            "該月份異動數量與紀錄不一致，無法撤銷；請核對是否曾修改統計資料"
          );

        if (
          (event.type === "new" && bs.data()!.rented < 1) ||
          (event.type === "exit" && bs.data()!.vacant < 1)
        )
          throw new Error("倉位現況與異動紀錄不一致，無法撤銷");

        const delta =
          event.type === "new" ? -1 :
          event.type === "exit" ? 1 : 0;

        const old = bs.data()!;

        t.update(u, {
          ...(event.previousLease || {
            leasePeriod: "",
            leaseStart: null,
            leaseEnd: null,
          }),
          vacantSince: event.type === "new" ? event.previousLease?.vacantSince || null : null,
          status: event.type === "new" ? "vacant" : "rented",
          lastEventId: event.previousEventId,
          lastEventDate: event.previousEventDate,
          updatedAt: time(),
        });

        t.update(e, {
          voided: true,
          voidedBy: me,
          voidedAt: time(),
          voidMode: "rollback",
        });

        t.update(b, {
          rented: old.rented + delta,
          vacant: old.vacant - delta,
          revision: old.revision + 1,
          updatedAt: time(),
        });

        t.set(
          m,
          { [event.type]: (ms.data()?.[event.type] || 0) - 1 },
          { merge: true },
        );

        if (ns.data()?.source !== "import") {
          t.set(
            n,
            {
              source: "live",
              total: old.total,
              rented: old.rented + delta,
              snapshotDate: taipeiDate(),
            },
            { merge: true },
          );
        }
      });

      return {};
    }
    case "saveUnit": {
      if(data.markRenewalPending && !data.remove)return savePendingUnit(data);
      const unit = normalizeUnits([
          { ...data,
          price: Number(data.price || 0)
        }
      ])[0];

      const branchDoc = branch(data.branchId);

      const unitDoc = doc(
        db,
        "branches",
        data.branchId,
        "units",
        unit.code
      );

      const monthDoc = doc(
        db,
        "branches",
        data.branchId,
        "months",
        taipeiDate().slice(0, 7)
      );

      await runTransaction(db, async (transaction) => {
        const [
          branchSnapshot,
          unitSnapshot,
          monthSnapshot
        ] = await Promise.all([
          transaction.get(branchDoc),
          transaction.get(unitDoc),
          transaction.get(monthDoc)
        ]);

        if (
          !branchSnapshot.exists() ||
          branchSnapshot.data().importing
        ) {
          throw new Error(
            "據點不存在或正在匯入"
          );
        }

        const old = branchSnapshot.data();
        let delta = 0;

        if (data.remove) {
          if (
            !unitSnapshot.exists() ||
            unitSnapshot.data().status ===
              "rented"
          ) {
            throw new Error(
              "已出租倉位須先退租"
            );
          }

          delta =
            unitSnapshot.data().missing
              ? 0
              : -1;

          transaction.delete(unitDoc);
        } else {
          delta = unitSnapshot.exists()
            ? 0
            : 1;

          if (unitSnapshot.data()?.status === "rented" && "leasePeriod" in data && !unit.leasePeriod)
            throw new Error("已出租倉位必須填寫租期；若已退租請使用退租操作");
          if ((!unitSnapshot.exists() || unitSnapshot.data()?.status === "vacant") && unit.leasePeriod)
            throw new Error("空倉請先登記承租，再填寫租期");
          transaction.set(
            unitDoc,
            {
              ...unit,
              ...pricingUpdate(
                unitSnapshot.data(),
                unit,
                taipeiDate(),
                old.inventoryDate
              ),
              ...(!unitSnapshot.exists()
                ? {
                    vacantSince: null, status: "vacant",
                    missing: false,
                    lastEventDate:
                      taipeiDate(),
                    lastEventId: null
                  }
                : {}),
              updatedAt: time()
            },
            { merge: true }
          );
        }

        transaction.update(branchDoc, {
          total: old.total + delta,
          vacant: old.vacant + delta,
          revision: old.revision + 1,
          updatedAt: time()
        });

        if (
          monthSnapshot.data()?.source !==
          "import"
        ) {
          transaction.set(
            monthDoc,
            {
              source: "live",
              total: old.total + delta,
              rented: old.rented,
              snapshotDate: taipeiDate()
            },
            { merge: true }
          );
        }
      });

      return {};
    }

    case "removeImport": {
      return removeImport(data);
    }
    case "deletePendingRenewal": return deletePendingRenewal(data);
    case "confirmRenewalPayment": return confirmRenewalPayment(data);
    case "reviewInventory": return reviewInventory(data);
    case "importInventory": {
      const files = sourceFiles(data, "inventory");
      const units = normalizeUnits(data.units);

      const codes = new Set(
        units.map((unit) => unit.code)
      );

      const vacant = new Set<string>(units.filter(unit => !unit.leasePeriod).map(unit => unit.code));
      if (data.units.some((unit: any) => typeof unit.leasePeriod !== "string"))
        throw new Error("請使用含「租期」欄的單一倉位表重新匯入");
      if (data.vacantCodes.some((code: string) => !vacant.has(code)))
        throw new Error("租期與空倉判定不一致");

      if (
        vacant.size !==
          data.vacantCodes.length ||
        [...vacant].some(
          (code) => !codes.has(code)
        )
      ) {
        throw new Error(
          "空倉重複或不存在於總倉表"
        );
      }

      if (
        !validDate(data.effectiveDate) ||
        data.effectiveDate > taipeiDate()
      ) {
        throw new Error("盤點日期不合法");
      }

      const branchDoc = branch(data.branchId);
      const token = crypto.randomUUID();
      let previousInventoryDate: string | null = null;

      await runTransaction(db, async (transaction) => {
        const snapshot =
          await transaction.get(branchDoc);

        if (!snapshot.exists()) {
          throw new Error("據點不存在");
        }

        previousInventoryDate =
          snapshot.data().inventoryDate || null;

        if (
          previousInventoryDate &&
          data.effectiveDate < previousInventoryDate
        ) {
          throw new Error(
            "盤點日期不得早於上次盤點；舊月份請使用歷史 KPI 匯入"
          );
        }
        const lock = snapshot.data().importing;

        if (
          lock &&
          Date.now() - lock.startedAt <
            600000
        ) {
          throw new Error(
            "匯入正在執行，若已中斷請十分鐘後重試"
          );
        }

        transaction.update(branchDoc, {
          importing: {
            token,
            by: me,
            startedAt: Date.now()
          },
          revision:
            snapshot.data().revision + 1
        });
      });

      const old = await getDocs(
        collection(
          db,
          "branches",
          data.branchId,
          "units"
        )
      );

      const previousUnits = new Map(
        old.docs.map((item) => [
          item.id,
          item.data(),
        ])
      );
      const all: any[] = units.map(
        (unit) => ({
          ...unit,
          ...pricingUpdate(
            previousUnits.get(unit.code),
            unit,
            data.effectiveDate,
            previousInventoryDate
          ),
          vacantSince: vacancyDate(previousUnits.get(unit.code), vacant.has(unit.code) ? "vacant" : "rented", data.effectiveDate),
          status: vacant.has(unit.code)
            ? "vacant"
            : "rented",
          missing: false,
          archived: false,
          lastEventDate:
            data.effectiveDate,
          lastEventId: null
        })
      );

      for (const existing of old.docs) {
        if (!codes.has(existing.id)) {
          all.push({
            ...existing.data(),
            code: existing.id,
            missing: true
          });
        }
      }

      for (
        let index = 0;
        index < all.length;
        index += 350
      ) {
        const batch = writeBatch(db);

        for (
          const unit of
          all.slice(index, index + 350)
        ) {
          batch.set(
            doc(
              db,
              "branches",
              data.branchId,
              "units",
              unit.code
            ),
            {
              ...unit,
              updatedAt: time()
            }
          );
        }

        await batch.commit();
      }

      const stats = inventoryStats(all);

      const monthDoc = doc(
        db,
        "branches",
        data.branchId,
        "months",
        taipeiDate().slice(0, 7)
      );

      await runTransaction(db, async (transaction) => {
        const [
          branchSnapshot,
          monthSnapshot
        ] = await Promise.all([
          transaction.get(branchDoc),
          transaction.get(monthDoc)
        ]);

        if (
          branchSnapshot.data()?.importing
            ?.token !== token
        ) {
          throw new Error(
            "匯入鎖定已變更"
          );
        }

        transaction.update(branchDoc, {
          ...stats,
          importing: deleteField(),
          inventoryDate:
            data.effectiveDate,
          inventorySource: { ...files, id: token },
          revision:
            branchSnapshot.data()!.revision +
            1,
          updatedAt: time()
        });

        if (
          monthSnapshot.data()?.source !==
          "import"
        ) {
          transaction.set(
            monthDoc,
            {
              source: "live",
              total: stats.total,
              rented: stats.rented,
              snapshotDate: taipeiDate()
            },
            { merge: true }
          );
        }

        transaction.set(
          doc(
            collection(
              db,
              "branches",
              data.branchId,
              "imports"
            )
          ),
          {
            ...stats,
            effectiveDate:
              data.effectiveDate,
            missing: all
              .filter(
                (unit) => unit.missing
              )
              .map(
                (unit) => unit.code
              ),
            by: me,
            createdAt: time()
          }
        );
      });

      return stats;
    }

    case "backfillRenewals": {
      const {backfillRenewals}=await import('./backfill-renewals');
      return backfillRenewals(data.branchId,data.months,data.existingMonths,data.kpiFile);
    }
    case "importKpi": {
      const branchDoc = branch(data.branchId);

      if (data.removeMonth) {
        await runTransaction(
          db,
          async (transaction) => {
            const ref = doc(
              db,
              "branches",
              data.branchId,
              "months",
              data.removeMonth
            );

            const snapshot =
              await transaction.get(ref);

            if (
              snapshot.data()?.source !==
              "import"
            ) {
              throw new Error(
                "只能移除歷史匯入統計"
              );
            }

            transaction.delete(ref);
          }
        );

        return {};
      }

      const files = sourceFiles(data, "kpi");
      const months = data.months;

      if (
        !Array.isArray(months) ||
        !months.length ||
        months.length > 240
      ) {
        throw new Error(
          "KPI 資料筆數不合法"
        );
      }

      const seen = new Set();

      const existingMonths = new Map<string, any>();
      for (const month of months) {
        if (
          !/^\d{4}-(0[1-9]|1[0-2])$/.test(
            month.month
          ) ||
          month.month >=
            taipeiDate().slice(0, 7) ||
          seen.has(month.month)
        ) {
          throw new Error(
            "只能匯入不重複且已結算月份"
          );
        }

        seen.add(month.month);

        for (const key of [
          "total",
          "rented",
          "new",
          "renew",
          "exit"
        ]) {
          if (
            month[key] !== null &&
            (
              !Number.isInteger(
                month[key]
              ) ||
              month[key] < 0
            )
          ) {
            throw new Error(
              `${month.month} 數字不合法`
            );
          }
        }

        if (month.total !== null && month.rented !== null && month.rented > month.total) {
          throw new Error(
            `${month.month} 已出租數不可大於總倉數`
          );
        }
      }

      await runTransaction(db, async (transaction) => {
        const snapshot =
          await transaction.get(branchDoc);

        if (
          !snapshot.exists() ||
          snapshot.data().importing
        ) {
          throw new Error(
            "據點不存在或正在匯入"
          );
        }

        for (const month of months) {
          const old =
            await transaction.get(
              doc(
                db,
                "branches",
                data.branchId,
                "months",
                month.month
              )
            );

          existingMonths.set(
            month.month,
            old.data()
          );

          if (
            old.exists() &&
            old.data().source !== "import"
          ) {
            throw new Error(
              `${month.month} 已有即時紀錄，不能覆蓋`
            );
          }
        }

        for (const month of months) {
          transaction.set(
            doc(
              db,
              "branches",
              data.branchId,
              "months",
              month.month
            ),
            {
              month: month.month,
              total: month.total,
              rented: month.rented,
              new: month.new,
              renew: month.renew,
              renewByTerm: validateRenewCounts(month.renewByTerm,month.renew) || existingMonths.get(month.month)?.renewByTerm || null,
              exit: month.exit,
              kpiMetrics: month.kpiMetrics || {revenue:null,performance:null,occupancy:null},
              amounts: frozenAmounts(
                existingMonths.get(month.month),
                month.amounts
              ),
              source: "import",
              sourceFile: files.kpi,
              amountSourceFile:
                existingMonths.get(month.month)?.amounts &&
                Object.keys(existingMonths.get(month.month).amounts).length
                  ? existingMonths.get(month.month).amountSourceFile ||
                    "舊資料未記錄檔名"
                  : files.kpi,
              updatedBy: me,
              updatedAt: time()
            }
          );
        }
      });

      return {};
    }

    default:
      throw new Error("未知操作");
  }
}

// storeasy-opening-month-v1

// storeasy-annual-renew-backfill-v2

// storeasy-work-team-v1

// storeasy-transfers-v1

// storeasy-inventory-review-v1
