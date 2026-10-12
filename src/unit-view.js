
export function compareUnits(a, b, sortBy = "code") {
  const code = String(a.code || "").localeCompare(
    String(b.code || ""),
    "zh-Hant",
    { numeric: true }
  );

  const volume = Number(a.volume || 0) - Number(b.volume || 0);

  return (sortBy === "volume" ? volume || code : code) ||
    String(a.branchName || "").localeCompare(
      String(b.branchName || ""),
      "zh-Hant",
      { numeric: true }
    );
}

export function activityUsageDetails(events, units, activity, month) {
  const lookup = new Map(
    units.map(unit => [`${unit.branchId}/${unit.code}`, unit])
  );

  return events
    .filter(event =>
      !event.voided &&
      event.month === month &&
      event.branchId === activity.branchId &&
      event.activities?.some(item => item.id === activity.id)
    )
    .map(event => {
      const current = lookup.get(
        `${event.branchId}/${event.code}`
      );
      const snapshot = event.unitSnapshot;

      return {
        ...event,
        details: snapshot || current || event.priceSnapshot || {},
        historical: !!snapshot,
      };
    })
    .sort(
      (a, b) =>
        b.date.localeCompare(a.date) || compareUnits(a, b)
    );
}
