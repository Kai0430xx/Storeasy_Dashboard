
import { validDate, taipeiDate } from "./domain.js";

export function parseLease(value) {
  const text = String(value ?? "").normalize("NFKC").trim();
  if (!text) {
    return { leasePeriod: "", leaseStart: null, leaseEnd: null };
  }

  const match = text.match(
    /^(\d{4})[\/.-](\d{1,2})[\/.-](\d{1,2})\s*(?:-|—|–|~|至)\s*(\d{4})[\/.-](\d{1,2})[\/.-](\d{1,2})$/
  );

  if (!match) {
    throw new Error(
      "租期格式不正確，請使用 2026/10/08－2027/04/07"
    );
  }

  const date = offset =>
    `${match[offset]}-${match[offset + 1].padStart(2, "0")}-${match[offset + 2].padStart(2, "0")}`;

  const leaseStart = date(1);
  const leaseEnd = date(4);

  if (
    !validDate(leaseStart) ||
    !validDate(leaseEnd) ||
    leaseStart > leaseEnd
  ) {
    throw new Error("租期日期不存在，或結束日早於開始日");
  }

  return {
    leasePeriod:
      `${leaseStart.replace(/-/g, "/")}－${leaseEnd.replace(/-/g, "/")}`,
    leaseStart,
    leaseEnd,
  };
}

export function leaseStatus(unit, date = taipeiDate(), pending = []) {
  if (unit.missing) {
    return {
      key: "missing",
      label: "清單中消失",
      color: "warning",
    };
  }

  if (unit.status !== "rented") {
    return { key: "vacant", label: "空倉", color: "green" };
  }


  // unpaid-overdue-v1: payment overdue is independent of the new lease end.
  const unpaid = pending.some(row => {
    if (row.status !== 'pending' || row.branchId !== unit.branchId || row.code !== unit.code) return false;
    let start = row.leaseStart;
    if (!start) {
      try { start = parseLease(row.leasePeriod).leaseStart; }
      catch { return false; }
    }
    return validDate(start) && start <= date;
  });
  if (unpaid) return { key: 'overdue', label: '已逾期（待收款）', color: 'red' };
  if (!unit.leaseEnd) {
    return {
      key: "unknown",
      label: "已出租（租期未提供）",
      color: "blue",
    };
  }

  if (unit.leaseEnd < date) {
    return { key: "overdue", label: "已逾期", color: "red" };
  }

  const days = Math.round(
    (
      Date.parse(`${unit.leaseEnd}T00:00:00Z`) -
      Date.parse(`${date}T00:00:00Z`)
    ) / 86400000
  );

  return days <= 14
    ? { key: "expiring", label: "即將到期", color: "warning" }
    : { key: "active", label: "租期內", color: "blue" };
}
