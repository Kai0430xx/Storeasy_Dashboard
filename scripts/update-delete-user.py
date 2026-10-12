from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
files = {}

def read(name):
    return (root / name).read_text(encoding="utf-8")

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("替換位置不唯一：" + old[:80])
    return text.replace(old, new, 1)

if 'case "deleteUser"' in read("src/api.ts"):
    print("刪除帳號已更新。")
    raise SystemExit(0)

files["src/delete-user.ts"] = r'''
import { doc, runTransaction, serverTimestamp } from "firebase/firestore";
import { auth, db } from "./firebase";

export async function deleteUserAccount(data: any) {
  const me = auth.currentUser?.uid;
  if (!me) throw new Error("請先登入");
  if (
    typeof data.uid !== "string" ||
    !data.uid ||
    data.uid.includes("/")
  ) throw new Error("帳號識別碼不合法");
  if (data.uid === me)
    throw new Error("不能刪除目前登入的管理員帳號");

  const targetRef = doc(db, "users", data.uid);
  const deletedRef = doc(db, "deletedUsers", data.uid);

  await runTransaction(db, async transaction => {
    const [actor, target] = await Promise.all([
      transaction.get(doc(db, "users", me)),
      transaction.get(targetRef),
    ]);

    if (actor.data()?.role !== "admin")
      throw new Error("只有系統管理員可以刪除帳號");
    if (!target.exists())
      throw new Error("此帳號已刪除或不存在");

    transaction.set(deletedRef, {
      username: target.data().username,
      deletedBy: me,
      deletedAt: serverTimestamp(),
    });
    transaction.delete(targetRef);
  });

  return {};
}
'''

s = read("src/api.ts")
s = 'import { deleteUserAccount } from "./delete-user";\n' + s
s = replace(
    s,
    '    case "manageUser": {',
    '    case "deleteUser": { return deleteUserAccount(data); }\n'
    '    case "manageUser": {',
)
files["src/api.ts"] = s

s = read("src/main.tsx")
s = 'import { getDoc } from "firebase/firestore";\n' + s

start = s.index('  useEffect(() => {\n    if (!user) return;')
end = s.index('  useEffect(() => {\n    if (!profile) return;', start)

s = s[:start] + r'''  useEffect(() => {
    if (!user) return;
    let stopped = false;
    const stop = onSnapshot(
      doc(db, "users", user.uid),
      async snapshot => {
        if (stopped) return;
        setProfile(snapshot.exists() ? snapshot.data() : null);
        if (!snapshot.exists()) {
          setBranches([]);
          setData({});
          try {
            const removed = await getDoc(
              doc(db, "deletedUsers", user.uid)
            );
            if (
              !stopped &&
              auth.currentUser?.uid === user.uid &&
              removed.exists()
            ) {
              await signOut(auth);
              setError("此帳號已被管理員刪除，請聯絡管理員");
            }
          } catch (error) {
            if (!stopped) setError(friendly(error));
          }
        }
      },
      error => setError(friendly(error)),
    );
    return () => {
      stopped = true;
      stop();
    };
  }, [user]);
''' + s[end:]

button = r'''
{profile.role === "admin" && (
  <button
    className="text-button danger"
    disabled={busy || item.id === user.uid}
    title={item.id === user.uid ? "不能刪除自己" : "刪除系統帳號"}
    onClick={() => setModal({kind: "deleteUser", target: item})}
  >
    刪除帳號
  </button>
)}
'''

s, count = re.subn(
    r"(指派權限\s*</button>)",
    lambda match: match.group(1) + button,
    s,
    count=1,
)
if count != 1:
    raise RuntimeError("找不到帳號操作按鈕")

s = replace(
    s,
    'createUser: "建立帳號",',
    'createUser: "建立帳號", deleteUser: "刪除帳號",',
)

s = replace(
    s,
    '            {modal.kind === "assign" && (',
    r'''            {modal.kind === "deleteUser" && <>
              <p>確定刪除帳號「{modal.target.username}」？</p>
              <p>
                刪除後會立即移除系統帳號及據點權限，該帳號不能使用網站。
                既有營運紀錄保留。
              </p>
              <p className="hint">
                Firebase Authentication 的登入資料須由管理員到
                Firebase 控制台另行刪除。
              </p>
              <button
                className="primary danger"
                disabled={busy}
                onClick={() => run(
                  () => call("deleteUser", {uid: modal.target.id}),
                  "系統帳號及權限已刪除"
                )}
              >
                確認刪除帳號
              </button>
            </>}
            {modal.kind === "assign" && (''',
)
files["src/main.tsx"] = s

s = read("firestore.rules")
s = replace(
    s,
    '    function profile() {',
    r'''    function activeUser() {
      return signedIn()
        && exists(
          /databases/$(database)/documents/users/$(request.auth.uid)
        );
    }

    function profile() {''',
)

start = s.index('    function globalAccess()')
end = s.index('    function unlocked(', start)
s = (
    s[:start]
    + s[start:end].replace('signedIn()', 'activeUser()')
    + s[end:]
)

start = s.index('    match /users/{uid}')
end = s.index('    match /branches/{id}', start)
block = s[start:end]

block = replace(
    block,
    'allow create: if signedIn()',
    'allow create: if signedIn()'
    ' && !exists(/databases/$(database)/documents/deletedUsers/$(uid))',
)

block = replace(
    block,
    "allow delete: if false;",
    r'''allow delete: if activeUser()
      && profile().role == 'admin'
      && uid != request.auth.uid
      && existsAfter(
        /databases/$(database)/documents/deletedUsers/$(uid)
      )
      && getAfter(
        /databases/$(database)/documents/deletedUsers/$(uid)
      ).data.deletedBy == request.auth.uid
      && getAfter(
        /databases/$(database)/documents/deletedUsers/$(uid)
      ).data.deletedAt == request.time;''',
)

s = s[:start] + block + r'''
    match /deletedUsers/{uid} {
      allow read: if signedIn()
        && (uid == request.auth.uid || globalAccess());

      allow create: if activeUser()
        && profile().role == 'admin'
        && uid != request.auth.uid
        && request.resource.data.keys().hasOnly([
          'username', 'deletedBy', 'deletedAt'
        ])
        && request.resource.data.username == get(
          /databases/$(database)/documents/users/$(uid)
        ).data.username
        && request.resource.data.deletedBy == request.auth.uid
        && request.resource.data.deletedAt == request.time
        && !existsAfter(
          /databases/$(database)/documents/users/$(uid)
        );

      allow update, delete: if false;
    }

''' + s[end:]

files["firestore.rules"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
