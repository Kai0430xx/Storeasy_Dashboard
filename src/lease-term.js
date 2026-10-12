
import { validDate } from "./domain.js";

export function leaseTerm(lease) {
  const start = lease?.leaseStart;
  const end = lease?.leaseEnd;

  if (!validDate(start) || !validDate(end) || start > end) {
    return "unknown";
  }

  const [year, month, day] = start.split("-").map(Number);

  // 租期包含結束日。
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

  return { rows, counts };
}
