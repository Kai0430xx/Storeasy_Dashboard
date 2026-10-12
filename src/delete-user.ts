
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
