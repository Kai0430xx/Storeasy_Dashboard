from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}


def read(name):
    return (root / name).read_text(encoding="utf-8")


if 'voidMode: "history"' in read("src/api.ts"):
    print("管理員撤銷功能已更新。")
    raise SystemExit(0)

NEW_CASE = r'''
    case "voidEvent": {
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
'''

s = read("src/api.ts")
start = s.index('    case "voidEvent": {')
end = s.index('    case "saveUnit":', start)
files["src/api.ts"] = s[:start] + NEW_CASE + s[end:]

s = read("src/main.tsx")
start = s.index('{modal.kind === "void" && (')
end = s.index('{modal.kind === "deleteUnit" && (', start)

block, count = re.subn(
    r"<p>.*?</p>",
    '''<p>
                  撤銷 {modal.event.code} 在 {modal.event.date} 的{types[modal.event.type]}？
                  {profile?.role === "admin"
                    ? "管理員可以撤銷任一筆紀錄。較早紀錄只作廢並扣除可對應的即時異動筆數，保留目前倉位現況及後續租期；最後一筆在資料可安全回復時會回復前一狀態。匯入 KPI 彙總不會自動修改。"
                    : "只能撤銷該倉位最後一筆異動，並回復前一狀態。"}
                </p>''',
    s[start:end],
    count=1,
    flags=re.S,
)

if count != 1:
    raise RuntimeError("找不到撤銷確認文字")

files["src/main.tsx"] = s[:start] + block + s[end:]

s = read("firestore.rules")
start = s.index("match /events/{eventId} {")
end = s.index("match /activities/{activityId} {", start)
block = s[start:end]

pattern = (
    r"hasOnly\(\[\s*'voided',\s*'voidedBy',"
    r"\s*'voidedAt'\s*\]\)"
)

block, count = re.subn(
    pattern,
    "hasOnly(['voided','voidedBy','voidedAt','voidMode'])"
    " && (!('voidMode' in request.resource.data)"
    " || request.resource.data.voidMode == 'rollback')",
    block,
    count=1,
)

if count != 1:
    raise RuntimeError("找不到異動撤銷規則")

i = block.index("allow update: if ")
j = block.index(";", i)
condition = block[i + len("allow update: if "):j]

admin = """signedIn() && profile().role == 'admin' && unlocked(id)
          && !resource.data.voided && request.resource.data.voided == true
          && ('voidMode' in request.resource.data)
          && request.resource.data.voidMode == 'history'
          && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['voided','voidedBy','voidedAt','voidMode'])
          && request.resource.data.voidedBy == request.auth.uid
          && request.resource.data.voidedAt == request.time"""

block = (
    block[:i] +
    "allow update: if (" + condition + ") || (" + admin + ");" +
    block[j + 1:]
)

files["firestore.rules"] = s[:start] + block + s[end:]

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
