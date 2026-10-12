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

  const threshold = months => {
    const date = new Date(
      Date.UTC(year, month - 1 + months, 1)
    );

    const lastDay = new Date(
      Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth() + 1,
        0
      )
    ).getUTCDate();

    date.setUTCDate(Math.min(day, lastDay));

    return date.toISOString().slice(0, 10);
  };

  if (afterEnd >= threshold(12)) return "yearly";
  if (afterEnd >= threshold(6)) return "halfYear";
  if (afterEnd >= threshold(3)) return "quarterly";
  if (afterEnd >= threshold(1)) return "monthly";

  return "other";
}

export function rentalDetails(events, units, type, month) {
  const lookup = new Map(
    units.map(unit => [
      `${unit.branchId}/${unit.code}`,
      unit
    ])
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
        )
      };
    })
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) ||
        String(a.code).localeCompare(
          String(b.code),
          "zh-Hant",
          { numeric: true }
        )
    );

  const counts = {
    monthly: 0,
    quarterly: 0,
    halfYear: 0,
    yearly: 0,
    other: 0,
    unknown: 0
  };

  rows.forEach(row => counts[row.term]++);

  return { rows, counts };
}
