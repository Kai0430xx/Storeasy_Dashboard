const valid = n =>
  typeof n === 'number' && Number.isFinite(n) && n >= 0;

function comparison(current, previous) {
  const difference =
    current !== null && previous !== null
      ? current - previous
      : null;

  return {
    current,
    previous,
    difference,
    percent:
      difference !== null && previous > 0
        ? difference / previous * 100
        : null,
  };
}

export function revenueComparison(branches, data, month) {
  const previousMonth =
    `${Number(month.slice(0, 4)) - 1}${month.slice(4)}`;

  const amount = (id, period) => {
    const saved = data[id]?.months?.find(
      m => (m.id || m.month) === period,
    );
    const n =
      saved?.source === 'import'
        ? saved.kpiMetrics?.revenue
        : null;

    return valid(n) ? n : null;
  };

  const rows = branches.map(b => ({
    id: b.id,
    name: b.name,
    ...comparison(
      amount(b.id, month),
      amount(b.id, previousMonth),
    ),
  }));

  const matched = rows.filter(r => r.difference !== null);

  const total = {
    ...comparison(
      matched.length
        ? matched.reduce((sum, r) => sum + r.current, 0)
        : null,
      matched.length
        ? matched.reduce((sum, r) => sum + r.previous, 0)
        : null,
    ),
    count: matched.length,
  };

  return {rows, total, previousMonth};
}
