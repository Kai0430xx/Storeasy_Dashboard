import { validDate } from "./domain.js";

export function priceVersion(unit, effectiveDate) {
  return {
    effectiveDate,
    price: Number(unit.price || 0),
    unitPrice: Number(unit.unitPrice || 0),
  };
}

/** @param {string|null} [previousInventoryDate] */
export function pricingUpdate(
  previous,
  next,
  effectiveDate,
  previousInventoryDate = null
) {
  if (!validDate(effectiveDate)) {
    throw new Error("價格生效日期不合法");
  }

  const history = (previous?.priceHistory || []).map(
    (version) => ({ ...version })
  );

  if (previous && !history.length) {
    const knownDate =
      previous.priceEffectiveDate ||
      previousInventoryDate;

    if (knownDate && validDate(knownDate)) {
      history.push(priceVersion(previous, knownDate));
    }
  }

  const last = history.at(-1);

  if (last && effectiveDate < last.effectiveDate) {
    throw new Error(
      "新價格生效日期不得早於既有價格版本"
    );
  }

  if (
    !last ||
    last.price !== Number(next.price) ||
    last.unitPrice !== Number(next.unitPrice)
  ) {
    history.push(priceVersion(next, effectiveDate));
  }

  return {
    priceHistory: history,
    priceEffectiveDate: history.at(-1).effectiveDate,
  };
}

export function priceSnapshot(unit, date) {
  const versions = (unit.priceHistory || []).filter(
    (version) => version.effectiveDate <= date
  );

  const version = versions.at(-1);

  if (unit.priceHistory?.length && !version) {
    throw new Error(
      "此日期沒有可確認的歷史價格"
    );
  }

  return {
    ...priceVersion(
      version || unit,
      version?.effectiveDate ||
        unit.priceEffectiveDate ||
        null
    ),
    volume: Number(unit.volume || 0),
    dimensions: String(unit.dimensions || ""),
  };
}

export function kpiAmounts(rows, column) {
  const amounts = {};

  for (const row of rows) {
    const label = String(row[0] || "").trim();

    if (
      !/業績|金額|保險|滯納金/.test(label) ||
      /率|比較|數量/.test(label)
    ) {
      continue;
    }

    const raw = row[column];

    if (
      raw === null ||
      raw === undefined ||
      raw === ""
    ) {
      continue;
    }

    const value = Number(raw);

    if (!Number.isFinite(value)) {
      throw new Error(
        `KPI 金額不合法：${label}`
      );
    }

    amounts[label] = value;
  }

  return amounts;
}

export function frozenAmounts(existing, incoming) {
  return existing?.amounts &&
    Object.keys(existing.amounts).length
    ? existing.amounts
    : incoming || {};
}
