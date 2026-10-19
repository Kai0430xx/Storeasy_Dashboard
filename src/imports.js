import { kpiMetrics } from "./targets.js";
import { parseLease } from "./lease.js";
import { kpiAmounts } from "./pricing.js";
import ExcelJS from "exceljs";

export async function workbook(buffer) {
  if (buffer.byteLength > 20 * 1024 * 1024) {
    throw new Error("Excel 檔案上限為 20MB");
  }

  const book = new ExcelJS.Workbook();
  await book.xlsx.load(buffer);

  const result = {
    SheetNames: [],
    Sheets: {}
  };

  for (const sheet of book.worksheets) {
    if (
      sheet.rowCount > 20000 ||
      sheet.columnCount > 200
    ) {
      throw new Error(
        "工作表範圍過大，請移除多餘格式或空白欄列"
      );
    }

    result.SheetNames.push(sheet.name);
    result.Merges ||= {};
    result.Merges[sheet.name] = sheet.model.merges || [];

    const rows = [];

    sheet.eachRow(
      { includeEmpty: true },
      (row) => {
        const values = [];

        for (
          let index = 1;
          index <= row.cellCount;
          index++
        ) {
          const value = row.getCell(index).value;

          if (value === null) {
            values.push(null);
          } else if (typeof value !== "object") {
            values.push(value);
          } else if ("result" in value) {
            values.push(value.result ?? null);
          } else if ("richText" in value) {
            values.push(
              value.richText
                .map((text) => text.text)
                .join("")
            );
          } else if ("text" in value) {
            values.push(value.text);
          } else {
            values.push(null);
          }
        }

        rows.push(values);
      }
    );

    result.Sheets[sheet.name] = rows;
  }

  return result;
}

/** @param {{requirePrice?: boolean, requireLease?: boolean}} [options] */
export function parseUnits(
  book,
  sheetName = book.SheetNames[0],
  options = { requirePrice: true }
) {
  const raw = book.Sheets[sheetName];

  if (!raw?.length) {
    throw new Error("工作表沒有資料");
  }

  const normalize = value =>
    String(value ?? "")
      .normalize("NFKC")
      .replace(/\s/g, "")
      .replace(/\((?:NT\$|NTD|元|新臺幣|新台幣)\)/gi, "");

  const headers = raw[0].map(normalize);

  const column = names => {
    for (const name of names) {
      const index = headers.indexOf(normalize(name));
      if (index !== -1) return index;
    }
    return -1;
  };

  const codeIndex = column(["倉位", "倉位編號", "倉號"]);

  if (codeIndex < 0) {
    throw new Error("缺少「倉位」欄位");
  }

  const entries = raw
    .slice(1)
    .filter(row => String(row[codeIndex] ?? "").trim());

  const seen = new Set();

  for (const row of entries) {
    const code = String(row[codeIndex]).trim();

    if (seen.has(code)) {
      throw new Error(`倉位重複：${code}`);
    }

    seen.add(code);
  }

  if (!entries.length) return [];

  const leaseIndex = column(["租期"]);
  if (options.requireLease && leaseIndex < 0) throw new Error("缺少「租期」欄位；空倉請保留此欄並留空");
  const priceIndex = column([
    "月租",
    "月租金",
    "月租金額",
    "原價",
    "月繳",
    "金額"
  ]);

  if (options.requirePrice && priceIndex < 0) {
    throw new Error(
      "找不到月租金額欄位。請使用「月租、月租金、原價、月繳」其中一種欄名。"
    );
  }

  const dimensionsIndex = column([
    "尺寸 W*L*H",
    "尺寸",
    "尺寸W×L×H"
  ]);

  const volumeIndex = column(["材積", "材積數"]);
  const unitPriceIndex = column(["單價"]);
  const noteIndex = column(["備註"]);

  const number = (value, label, required = false) => {
    const text = String(value ?? "").normalize("NFKC").trim();

    if (!text) {
      if (required) {
        throw new Error(`${label} 空白，請補齊金額再匯入`);
      }
      return 0;
    }

    const cleaned = text.replace(
      /NT\$|NTD|TWD|新臺幣|新台幣|元|[$,\s]/gi,
      ""
    );

    const result = Number(cleaned);

    if (!cleaned || !Number.isFinite(result) || result < 0) {
      throw new Error(`${label} 數值不合法：${text}`);
    }

    return result;
  };

  return entries.map(row => {
    const code = String(row[codeIndex]).trim();

    return {
      code,
      ...(leaseIndex < 0 ? {} : (() => {
        try { return parseLease(row[leaseIndex]); }
        catch (error) { throw new Error(`倉位 ${code}：${error.message}`); }
      })()),
      dimensions:
        dimensionsIndex < 0
          ? ""
          : String(row[dimensionsIndex] ?? ""),

      volume: number(row[volumeIndex], `倉位 ${code} 材積`),

      unitPrice: number(
        row[unitPriceIndex],
        `倉位 ${code} 單價`
      ),

      price: options.requirePrice
        ? number(row[priceIndex], `倉位 ${code} 月租`, true)
        : 0,

            note: noteIndex < 0 ? "" : String(row[noteIndex] ?? "")
    };
  });
}

export function parseKpi(book) {
  const result = [];

  for (const name of book.SheetNames) {
    const rows = book.Sheets[name];
    const year = String(rows[0]?.[1] ?? "").match(/20\d{2}/)?.[0]
      || String(name).match(/20\d{2}/)?.[0];

    if (!year) continue;

    const find = keyword =>
      rows.find(row =>
        String(row[0] || "").includes(keyword)
      );

    const total = find("可出租總倉位");
    const rented = find("已出租倉位");
    const fresh = find("新約數量");
    const exit = find("出倉倉位數量");

    const renewRows = [
      "月租／續約",
      "季繳／續約",
      "半年／續約",
      "年約／續約"
    ].map(find);

    const num = (row, column) => {
      const raw = row?.[column];
      const text = String(raw ?? "")
        .normalize("NFKC")
        .trim();

      if (!text || /^(?:-|—|–|N\/A)$/i.test(text)) {
        return null;
      }

      // 例如 23/31：23 為分項件數，31 為當月合計。
      const split = renewRows.includes(row) &&
        text.match(/^(\d+)\s*\/\s*(\d+)$/);

      const value = Number(
        split ? split[1] : text.replace(/,/g, "")
      );

      if (!Number.isInteger(value) || value < 0) {
        throw new Error(
          `${name} ${column}月「${row?.[0] || "數量"}」數值不合法：${text}`
        );
      }

      return value;
    };

    for (let column = 1; column <= 12; column++) {
      const totalValue = num(total, column);
      const rentedValue = num(rented, column);

      if (totalValue === null && rentedValue === null) {
        continue;
      }

      const renewValues = renewRows.map(
        row => num(row, column)
      );

      result.push({
        month:
          `${year}-` +
          String(column).padStart(2, "0"),

        renewByTerm: Object.fromEntries(["monthly","quarterly","halfYear","yearly"].map((key,index)=>[key,renewValues[index]])),
        amounts: kpiAmounts(rows, column), kpiMetrics: kpiMetrics(rows, column, year),
        total: totalValue,
        rented: rentedValue,
        new: num(fresh, column),
        exit: num(exit, column),

        renew: renewValues.every(value => value !== null)
          ? renewValues.reduce((sum, value) => sum + value, 0)
          : null
      });
    }
  }

  if (!result.length) {
    throw new Error(
      "找不到可出租總倉位與已出租倉位的月度資料"
    );
  }

  return result.sort(
    (a, b) => a.month.localeCompare(b.month)
  );
}

// storeasy-annual-renew-backfill-v2
