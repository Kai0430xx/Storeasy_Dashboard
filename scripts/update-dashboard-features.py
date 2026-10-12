from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}


def read(name):
    return (root / name).read_text(encoding="utf-8")


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("找不到唯一替換位置：" + old[:100])
    return text.replace(old, new, 1)


def sub(text, pattern, new):
    text, count = re.subn(
        pattern, lambda m: new, text, count=1, flags=re.S
    )
    if count != 1:
        raise RuntimeError("找不到替換位置：" + pattern[:100])
    return text


if 'import RentalDetails from "./RentalDetails";' in read("src/main.tsx"):
    print("承租明細功能已套用，不重複修改。")
    raise SystemExit(0)

NEW_FILES = {}

NEW_FILES["src/lease-term.js"] = r'''
import { validDate } from "./domain.js";

export function leaseTerm(lease) {
  const start = lease?.leaseStart;
  const end = lease?.leaseEnd;

  if (!validDate(start) || !validDate(end) || start > end) {
    return "unknown";
  }

  const [year, month, day] = start.split("-").map(Number);
  const afterEnd = new Date(
    Date.parse(`${end}T00:00:00Z`) + 86400000
  ).toISOString().slice(0, 10);

  for (
    const [count, type] of [
      [1, "monthly"],
      [3, "quarterly"],
      [6, "halfYear"],
      [12, "yearly"],
    ]
  ) {
    const date = new Date(
      Date.UTC(year, month - 1 + count, 1)
    );
    const last = new Date(
      Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth() + 1,
        0
      )
    ).getUTCDate();

    date.setUTCDate(Math.min(day, last));

    if (date.toISOString().slice(0, 10) === afterEnd) {
      return type;
    }
  }

  return "other";
}

export function rentalDetails(events, units, type, month) {
  const lookup = new Map(
    units.map(unit => [`${unit.branchId}/${unit.code}`, unit])
  );

  const rows = events
    .filter(event =>
      !event.voided &&
      event.type === type &&
      event.month === month
    )
    .map(event => {
      const snapshot = event.unitSnapshot;

      return {
        ...event,
        details:
          snapshot ||
          lookup.get(`${event.branchId}/${event.code}`) ||
          event.priceSnapshot ||
          {},
        historical: !!snapshot,
        term: leaseTerm(
          type === "exit"
            ? event.previousLease || snapshot
            : snapshot
        ),
      };
    })
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) ||
        String(a.code).localeCompare(
          String(b.code), "zh-Hant", { numeric: true }
        )
    );

  const counts = {
    monthly: 0,
    quarterly: 0,
    halfYear: 0,
    yearly: 0,
    other: 0,
    unknown: 0,
  };

  rows.forEach(row => counts[row.term]++);

  return { rows, counts };
}
'''

NEW_FILES["src/RentalDetails.tsx"] = r'''
import React from "react";
import { rentalDetails } from "./lease-term.js";

type Row = Record<string, any>;

export default function RentalDetails({
  type, month, events, units, total,
}: {
  type: string;
  month: string;
  events: Row[];
  units: Row[];
  total: number | null;
}) {
  const result = rentalDetails(events, units, type, month);
  const rows: Row[] = result.rows;
  const counts: Row = result.counts;
  const names: Row = {
    new: "新承租",
    renew: "續約",
    exit: "退租",
  };

  return (
    <>
      <h2>{names[type]}明細 · {month}</h2>
      <p>
        統計總筆數：{total ?? "無資料"}；
        可查明細：{rows.length} 筆。
      </p>

      {type !== "exit" && (
        <div className="preview-counts rental-summary">
          {Object.entries({
            monthly: "月租",
            quarterly: "季租",
            halfYear: "半年租",
            yearly: "年租",
            other: "其他租期",
            unknown: "租期未記錄",
          }).map(([key, label]) => (
            <span key={key}>
              {label} <b>{counts[key]} 筆</b>
            </span>
          ))}
        </div>
      )}

      <p className="hint">
        按起訖日期辨識 1、3、6、12 個月租期。
        KPI 匯入只有彙總，未提供倉位明細；
        舊異動未記錄租期時不使用現況推算歷史分類。
      </p>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>倉位／據點</th>
              <th>尺寸</th>
              <th>材積</th>
              <th>月租</th>
              <th>租期</th>
              <th>備註</th>
              <th>資料時間</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={`${row.branchId}/${row.id}`}>
                <td>{row.date}</td>
                <td>
                  {row.code}
                  <small className="table-sub">
                    {row.branchName}
                  </small>
                </td>
                <td>{row.details.dimensions || "—"}</td>
                <td>{row.details.volume ?? "—"}</td>
                <td>
                  {row.details.price == null
                    ? "—"
                    : `NT$ ${Number(row.details.price).toLocaleString()}`}
                </td>
                <td>
                  {(type === "exit"
                    ? row.previousLease?.leasePeriod
                    : row.details.leasePeriod) || "未記錄"}
                </td>
                <td>{row.details.note || "—"}</td>
                <td>
                  {row.historical ? "異動時" : "現況／舊紀錄"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!rows.length && (
          <p>此月份沒有可查詢的倉位異動明細。</p>
        )}
      </div>
    </>
  );
}
'''

NEW_FILES["src/remove-activity.ts"] = r'''
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

export async function removeActivity(data: any) {
  if (!auth.currentUser) throw new Error("請先登入");

  if (
    ![data.branchId, data.activityId].every(
      value =>
        typeof value === "string" &&
        value &&
        !value.includes("/")
    )
  ) {
    throw new Error("據點或活動不合法");
  }

  const by = auth.currentUser.uid;
  const branchDoc = doc(db, "branches", data.branchId);
  const activityDoc = doc(
    branchDoc, "activities", data.activityId
  );
  const token = crypto.randomUUID();

  await runTransaction(db, async transaction => {
    const [branch, activity] = await Promise.all([
      transaction.get(branchDoc),
      transaction.get(activityDoc),
    ]);

    if (!branch.exists() || !activity.exists()) {
      throw new Error("據點或活動不存在");
    }

    const lock = branch.data().importing;
    const resume =
      lock?.operation === "removeActivity" &&
      lock.activityId === data.activityId &&
      lock.by === by;

    if (
      lock &&
      !resume &&
      Date.now() - lock.startedAt < 600000
    ) {
      throw new Error(
        "據點正在匯入或刪除資料，請稍後再試"
      );
    }

    transaction.update(branchDoc, {
      importing: {
        token,
        by,
        startedAt: Date.now(),
        operation: "removeActivity",
        activityId: data.activityId,
      },
      revision: branch.data().revision + 1,
    });

    transaction.update(activityDoc, {
      archived: true,
      deleting: true,
      updatedBy: by,
      updatedAt: serverTimestamp(),
    });
  });

  const events = await getDocs(
    collection(branchDoc, "events")
  );

  const matches = events.docs.filter(snapshot =>
    snapshot.data().activities?.some(
      (item: any) => item.id === data.activityId
    )
  );

  for (let index = 0; index < matches.length; index += 350) {
    const batch = writeBatch(db);

    for (const event of matches.slice(index, index + 350)) {
      const activities = event.data().activities;

      batch.update(event.ref, {
        activities: activities.filter(
          (item: any) => item.id !== data.activityId
        ),
        activityRemoval: {
          activity: activities.find(
            (item: any) => item.id === data.activityId
          ),
          by,
          token,
          at: serverTimestamp(),
        },
      });
    }

    await batch.commit();
  }

  await runTransaction(db, async transaction => {
    const branch = await transaction.get(branchDoc);

    if (branch.data()?.importing?.token !== token) {
      throw new Error(
        "鎖定已變更，請重新整理後再試"
      );
    }

    transaction.delete(activityDoc);
    transaction.update(branchDoc, {
      importing: deleteField(),
      revision: branch.data()!.revision + 1,
      updatedAt: serverTimestamp(),
    });
  });

  return { removedUses: matches.length };
}
'''

files.update(NEW_FILES)

s = read("src/lease.js")
s = sub(
    s,
    r'\s*if \(unit\.leaseStart > date\) \{\s*return \{ key: "upcoming".*?\};\s*\}',
    "",
)
files["src/lease.js"] = s

s = read("src/api.ts")
s = 'import { removeActivity } from "./remove-activity";\n' + s
s = replace(
    s,
    '    case "voidEvent": {',
    '    case "removeActivity": {\n      return removeActivity(data);\n    }\n    case "voidEvent": {',
)

start = s.index('    case "voidEvent":')
end = s.index('    case "saveUnit":', start)
block = replace(
    s[start:end],
    "        const delta =",
    '''        if (!Number.isInteger(monthSnapshot.data()?.[event.type]) || monthSnapshot.data()![event.type] < 1)
          throw new Error("該月份異動數量與紀錄不一致，無法撤銷；請核對是否曾修改統計資料");
        if ((event.type === "new" && branchSnapshot.data()!.rented < 1) || (event.type === "exit" && branchSnapshot.data()!.vacant < 1))
          throw new Error("倉位現況與異動紀錄不一致，無法撤銷");
        const delta =''',
)
s = s[:start] + block + s[end:]
files["src/api.ts"] = s

s = read("src/firebase.ts")
s = replace(
    s,
    "  return execute(name, data);",
    '''  try {
    return await execute(name, data);
  } catch (error: any) {
    if (error?.code === "permission-denied" && ["voidEvent", "removeActivity"].includes(name))
      throw new Error("Firebase 規則拒絕此操作。請確認最新 firestore.rules 已在 Firebase 發布；若已發布，請核對該倉位與月份統計是否一致。");
    throw error;
  }''',
)
files["src/firebase.ts"] = s

s = read("src/main.tsx")
s = 'import RentalDetails from "./RentalDetails";\n' + s
s = replace(
    s,
    'page === "units" || page === "imports" || page === "activities"',
    'page === "units" || page === "imports" || page === "activities" || page === "dashboard"',
)
s = replace(
    s,
    '<option value="upcoming">尚未起租</option>',
    "",
)

start = s.index('className="flow-row"')
start = s.rfind("<div", 0, start)
end = s.index("))}", start)
block = sub(
    s[start:end],
    r'<div\s+className="flow-row"\s+key=\{key\}\s*>',
    '<button type="button" className="flow-row" key={key} aria-label={`查看${types[key]}明細`} onClick={() => setModal({kind:"rentalDetails",type:key,month,total:value})}>',
)
position = block.rfind("</div>")
block = (
    block[:position] +
    block[position:].replace("</div>", "</button>", 1)
)
s = s[:start] + block + s[end:]

start = s.index("<h2>活動使用概況</h2>")
end = s.index('<div className="activity-summary">', start)
block = sub(
    s[start:end],
    r"</div>\s*</div>",
    '''</div>
                      {canWrite && <button className="text-button danger" aria-label="刪除活動" title="刪除活動設定及使用紀錄" onClick={() => setModal({kind:"chooseActivityDelete"})}><X size={20}/></button>}
                    </div>''',
)
s = s[:start] + block + s[end:]

start = s.index('<div className="activity-summary">')
end = s.index('{page === "units" && (', start)
block = sub(
    s[start:end],
    r"activity\.month === month,",
    "activity.month === month && !activity.deleting,",
)
block = sub(
    block,
    r"<span>\s*\{activity\.branchName\} · \{activity\.name\}\s*</span>",
    '<button className="text-button" onClick={() => setModal({kind:"activityUsage",activity,month})}>{activity.branchName} · {activity.name}</button>',
)
s = s[:start] + block + s[end:]

s = replace(
    s,
    '["inventory", "kpi", "activityUsage"].includes(modal.kind)',
    '["inventory", "kpi", "activityUsage", "rentalDetails"].includes(modal.kind)',
)
s = replace(
    s,
    'activityUsage: "活動使用明細",',
    '''activityUsage: "活動使用明細",
                  rentalDetails: "承租動態明細",
                  chooseActivityDelete: "選擇要刪除的活動",
                  removeActivity: "刪除活動與使用紀錄",''',
)
s = replace(
    s,
    '{modal.kind === "activityUsage" && (',
    '''{modal.kind === "rentalDetails" && <RentalDetails type={modal.type} month={modal.month} total={modal.total} events={events} units={units} />}
            {modal.kind === "chooseActivityDelete" && <>
              <p>請選擇要刪除的活動，下一步會確認刪除範圍。</p>
              {activities.filter(activity => activity.month === month).map(activity => <div className="activity-delete-row" key={`${activity.branchId}/${activity.id}`}>
                <span>{activity.branchName} · {activity.name}{activity.deleting ? "（刪除未完成，可重試）" : ""}</span>
                <button className="text-button danger" onClick={() => setModal({kind:"removeActivity",activity})}>刪除</button>
              </div>)}
            </>}
            {modal.kind === "removeActivity" && <>
              <p>刪除「{modal.activity.branchName} · {modal.activity.name}」？</p>
              <p>此活動設定及所有月份的活動使用連結會刪除；承租、續約、退租紀錄與統計數量保留。此操作不會刪除其他活動。</p>
              <button className="primary danger" disabled={busy} onClick={() => run(() => call("removeActivity",{branchId:modal.activity.branchId,activityId:modal.activity.id}),"活動及使用紀錄已刪除")}>確認刪除活動</button>
            </>}
            {modal.kind === "activityUsage" && (''',
)
files["src/main.tsx"] = s

files["src/style.css"] = read("src/style.css") + '''
button.flow-row {
  width:100%;
  text-align:left;
  background:transparent;
  border:0;
  border-bottom:1px solid var(--border);
  color:inherit;
  cursor:pointer;
}
button.flow-row:hover { background:#f4f7fb; }
.activity-delete-row {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  padding:12px 0;
}
.rental-summary {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
  gap:12px;
}
'''

s = read("firestore.rules")
s = replace(
    s,
    "|| eventMatches()",
    "|| (request.resource.data.lastEventId != null && eventMatches())",
)
s = replace(
    s,
    "|| undoMatches()",
    "|| (resource.data.lastEventId != null && undoMatches())",
)

start = s.index("match /events/{eventId} {")
end = s.index("match /activities/{activityId} {", start)
block = s[start:end]
block = replace(
    block,
    "match /events/{eventId} {",
    """match /events/{eventId} {
        function removesActivity() {
          let r = request.resource.data.activityRemoval;
          let lock = get(/databases/$(database)/documents/branches/$(id)).data.importing;
          let activity = get(/databases/$(database)/documents/branches/$(id)/activities/$(r.activity.id)).data;
          return request.resource.data.diff(resource.data).affectedKeys().hasOnly(['activities','activityRemoval'])
            && request.resource.data.activities is list
            && resource.data.activities.hasAny([r.activity])
            && request.resource.data.activities == resource.data.activities.removeAll([r.activity])
            && r.by == request.auth.uid && r.at == request.time && r.token == lock.token
            && lock.operation == 'removeActivity' && lock.activityId == r.activity.id
            && activity.deleting == true && activity.archived == true && activity.updatedBy == request.auth.uid;
        }""",
)
i = block.index("allow update: if ")
j = block.index(";", i)
condition = block[i + len("allow update: if "):j]
block = (
    block[:i] +
    "allow update: if (" + condition +
    ") || (branchEdit(id) && ownImport(id) && ('activityRemoval' in request.resource.data) && removesActivity());" +
    block[j + 1:]
)
s = s[:start] + block + s[end:]

start = s.index("match /activities/{activityId} {")
end = s.index("match /months/{month} {", start)
block = sub(
    s[start:end],
    r"allow create,\s*update: if branchEdit\(id\)",
    "allow create, update: if branchEdit(id) && (unlocked(id) || ownImport(id))",
)
block = replace(
    block,
    "allow delete: if false;",
    """allow delete: if branchEdit(id) && ownImport(id) && resource.data.deleting == true
          && get(/databases/$(database)/documents/branches/$(id)).data.importing.operation == 'removeActivity'
          && get(/databases/$(database)/documents/branches/$(id)).data.importing.activityId == activityId;""",
)
s = s[:start] + block + s[end:]
files["firestore.rules"] = s

for name, content in files.items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("已更新 " + name)
