
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
