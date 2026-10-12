import { parseLease } from "./lease.js";
export const roles = [
  "admin",
  "supervisor",
  "manager",
  "employee",
  "pending"
];

export function usernameEmail(name) {
  if (
    typeof name !== "string" ||
    !/^[a-zA-Z0-9_-]{2,32}$/.test(name)
  ) {
    throw new Error(
      "帳號須為 2～32 個英文字母、數字、底線或連字號"
    );
  }

  return `${name.toLowerCase()}@accounts.storeasy.invalid`;
}

export function taipeiDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
}

export function validDate(date) {
  if (
    typeof date !== "string" ||
    !/^\d{4}-\d{2}-\d{2}$/.test(date)
  ) {
    return false;
  }

  const parsed = new Date(`${date}T00:00:00Z`);

  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === date
  );
}

export function inventoryStats(units) {
  const active = units.filter((unit) => !unit.missing);

  return {
    total: active.length,
    rented: active.filter(
      (unit) => unit.status === "rented"
    ).length,
    vacant: active.filter(
      (unit) => unit.status === "vacant"
    ).length
  };
}

/** @returns {Array<{code:string,dimensions:string,volume:number,price:number,unitPrice:number,note:string,leasePeriod?:string,leaseStart?:string|null,leaseEnd?:string|null}>} */
export function normalizeUnits(rows) {
  if (
    !Array.isArray(rows) ||
    !rows.length ||
    rows.length > 10000
  ) {
    throw new Error("倉位清單須有 1～10,000 筆");
  }

  const seen = new Set();

  return rows.map((row) => {
    const code = String(row.code || "").trim();

    if (
      !code ||
      code.length > 80 ||
      /[\/]/.test(code) ||
      seen.has(code)
    ) {
      throw new Error(
        `倉位編號空白、重複或不合法：${code}`
      );
    }

    seen.add(code);

    const result = {
      code,
      ...("leasePeriod" in row ? parseLease(row.leasePeriod) : {}),
      dimensions: String(
        row.dimensions || ""
      ).slice(0, 100),
      volume: Number(row.volume || 0),
      price: Number(row.price || 0),
      unitPrice: Number(row.unitPrice || 0),
      note: String(row.note || "").slice(0, 500)
    };

    if (
      [
        result.volume,
        result.price,
        result.unitPrice
      ].some(
        (value) =>
          !Number.isFinite(value) || value < 0
      )
    ) {
      throw new Error(
        `倉位 ${code} 的金額或材積不合法`
      );
    }

    return result;
  });
}
