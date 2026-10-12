import {
  collection,
  doc,
  getDocs,
  runTransaction,
  writeBatch,
  serverTimestamp,
  deleteField,
} from "firebase/firestore";
import { auth, db } from "./firebase";
import { taipeiDate } from "./domain.js";

export function sourceFiles(data: any, kind: string) {
  const filename = (value: unknown) => {
    if (
      typeof value !== "string" ||
      !value.trim() ||
      value.length > 255
    ) {
      throw new Error(
        "缺少來源檔名，請重新選擇檔案並分析"
      );
    }

    return value.trim();
  };

  return kind === "inventory"
    ? {
        total: filename(data.totalFile),
      }
    : { kpi: filename(data.kpiFile) };
}

export async function removeImport(data: any) {
  if (!auth.currentUser) {
    throw new Error("請先登入");
  }

  if (!data.branchId || data.branchId.includes("/")) {
    throw new Error("據點不合法");
  }

  const branchDoc = doc(db, "branches", data.branchId);

  if (data.kind === "kpi") {
    if (
      !data.filename ||
      data.filename === "舊資料未記錄檔名"
    ) {
      throw new Error(
        "舊資料請使用歷史統計表的逐月移除功能"
      );
    }

    const months = await getDocs(
      collection(branchDoc, "months")
    );

    const matches = months.docs.filter(snapshot => {
      const month = snapshot.data();

      return month.source === "import" &&
        (
          month.sourceFile === data.filename ||
          month.amountSourceFile === data.filename
        );
    });

    if (!matches.length) {
      throw new Error(
        "此檔案目前沒有採用中的 KPI 資料"
      );
    }

    if (matches.length > 240) {
      throw new Error("月份過多，請逐月移除");
    }

    await runTransaction(db, async transaction => {
      const branch = await transaction.get(branchDoc);

      if (!branch.exists() || branch.data().importing) {
        throw new Error("據點不存在或正在匯入");
      }

      const fresh = await Promise.all(
        matches.map(snapshot =>
          transaction.get(snapshot.ref)
        )
      );

      for (const snapshot of fresh) {
        const month = snapshot.data();

        if (
          !month ||
          month.source !== "import" ||
          (
            month.sourceFile !== data.filename &&
            month.amountSourceFile !== data.filename
          )
        ) {
          throw new Error(
            "來源已變更，請重新整理後再刪除"
          );
        }
      }

      fresh.forEach(snapshot =>
        transaction.delete(snapshot.ref)
      );
    });

    return {};
  }

  if (data.kind !== "inventory") {
    throw new Error("匯入類型不合法");
  }

  const token = crypto.randomUUID();

  await runTransaction(db, async transaction => {
    const snapshot = await transaction.get(branchDoc);

    if (!snapshot.exists()) {
      throw new Error("據點不存在");
    }

    const branch = snapshot.data();

    if (
      (branch.inventorySource?.id || "legacy") !==
      data.sourceId
    ) {
      throw new Error(
        "目前採用的倉位資料已變更，請重新整理"
      );
    }

    const lock = branch.importing;

    if (
      lock &&
      Date.now() - lock.startedAt < 600000
    ) {
      throw new Error("據點正在匯入，請稍後再試");
    }

    transaction.update(branchDoc, {
      importing: {
        token,
        by: auth.currentUser!.uid,
        startedAt: Date.now(),
      },
      revision: branch.revision + 1,
    });
  });

  const units = await getDocs(
    collection(branchDoc, "units")
  );

  // 移出目前現況，保留價格歷史供重新匯入使用。
  for (let index = 0; index < units.docs.length; index += 350) {
    const batch = writeBatch(db);

    units.docs.slice(index, index + 350).forEach(
      snapshot => batch.update(snapshot.ref, {
        archived: true,
        missing: true,
        updatedAt: serverTimestamp(),
      })
    );

    await batch.commit();
  }

  const currentMonth = doc(
    branchDoc,
    "months",
    taipeiDate().slice(0, 7)
  );

  await runTransaction(db, async transaction => {
    const [branch, month] = await Promise.all([
      transaction.get(branchDoc),
      transaction.get(currentMonth),
    ]);

    if (branch.data()?.importing?.token !== token) {
      throw new Error("鎖定已變更");
    }

    transaction.update(branchDoc, {
      total: 0,
      rented: 0,
      vacant: 0,
      inventoryDate: deleteField(),
      inventorySource: deleteField(),
      importing: deleteField(),
      revision: branch.data()!.revision + 1,
      updatedAt: serverTimestamp(),
    });

    if (month.data()?.source !== "import") {
      transaction.set(
        currentMonth,
        {
          source: "live",
          total: 0,
          rented: 0,
          snapshotDate: taipeiDate(),
        },
        { merge: true }
      );
    }
  });

  return {};
}
