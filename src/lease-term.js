
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
