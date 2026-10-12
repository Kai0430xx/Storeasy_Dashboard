import { initializeApp } from "firebase/app";
import { getAuth, connectAuthEmulator } from "firebase/auth";
import {
  getFirestore,
  connectFirestoreEmulator
} from "firebase/firestore";

export const config = {
  apiKey: "AIzaSyDvlHZf5Gs25vW5vQmZ6-PZXFUoXbJFZn4",
  authDomain: "storeasy-dashboard.firebaseapp.com",
  projectId:
    import.meta.env.VITE_USE_EMULATORS === "true"
      ? "demo-storeasy"
      : "storeasy-dashboard",
  storageBucket: "storeasy-dashboard.firebasestorage.app",
  messagingSenderId: "587402672132",
  appId: "1:587402672132:web:7944613b6d9074c8e99d51"
};

const app = initializeApp(config);

export const auth = getAuth(app);
export const db = getFirestore(app);

if (import.meta.env.VITE_USE_EMULATORS === "true") {
  connectAuthEmulator(auth, "http://127.0.0.1:9099", {
    disableWarnings: true
  });

  connectFirestoreEmulator(db, "127.0.0.1", 8080);
}

export async function call(name: string, data: unknown) {
  const { execute } = await import("./api");
  return execute(name, data);
}

export const loginEmail = (username: string) => {
  if (!/^[a-zA-Z0-9_-]{2,32}$/.test(username)) {
    throw new Error(
      "帳號須為 2～32 個英文字母、數字、底線或連字號"
    );
  }

  return `${username.toLowerCase()}@accounts.storeasy.invalid`;
};
