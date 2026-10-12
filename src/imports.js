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

export function parseUnits(
  book,
  sheetName = book.SheetNames[0]
) {
  const raw = book.Sheets[sheetName];

  if (!raw?.length) {
    throw new Error("工作表沒有資料");
  }

  const keys = raw[0].map(
    (key) => String(key || "")
  );

  if (!keys.includes("倉位")) {
    throw new Error("缺少「倉位」欄位");
  }

  const rows = raw.slice(1).map((row) =>
    Object.fromEntries(
      raw[0].map((key, index) => [
        String(key || ""),
        row[index] ?? ""
      ])
    )
  );

  const result = rows
    .filter(
      (row) => String(row["倉位"]).trim()
    )
    .map((row) => ({
      code: String(row["倉位"]).trim(),
      dimensions: String(
        row["尺寸 W*L*H"] ||
        row["尺寸"] ||
        ""
      ),
      volume: Number(row["材積"] || 0),
      unitPrice: Number(row["單價"] || 0),
      price: Number(
        row["月租"] || row["金額"] || 0
      ),
      note: String(row["備註"] || "")
    }));

  const seen = new Set();

  for (const unit of result) {
    if (seen.has(unit.code)) {
      throw new Error(
        `倉位重複：${unit.code}`
      );
    }

    seen.add(unit.code);

    if (
      [
        unit.volume,
        unit.unitPrice,
        unit.price
      ].some(
        (value) =>
          !Number.isFinite(value) || value < 0
      )
    ) {
      throw new Error(
        `倉位 ${unit.code} 數值不合法`
      );
    }
  }

  return result;
}

export function parseKpi(book) {
  const result = [];

  for (const name of book.SheetNames) {
    const rows = book.Sheets[name];

    const year = String(
      rows[0]?.[1] || name
    ).match(/20\d{2}/)?.[0];

    if (!year) {
      continue;
    }

    const find = (keyword) =>
      rows.find((row) =>
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

    const num = (row, index) => {
      const value = row?.[index];

      if (
        value === null ||
        value === undefined ||
        value === ""
      ) {
        return null;
      }

      return Number(value);
    };

    for (let month = 1; month <= 12; month++) {
      const totalValue = num(total, month);
      const rentedValue = num(rented, month);

      if (
        totalValue === null &&
        rentedValue === null
      ) {
        continue;
      }

      const renewValues = renewRows.map(
        (row) => num(row, month)
      );

      result.push({
        month:
          `${year}-` +
          String(month).padStart(2, "0"),
        total: totalValue,
        rented: rentedValue,
        new: num(fresh, month),
        exit: num(exit, month),
        renew: renewValues.every(
          (value) => value !== null
        )
          ? renewValues.reduce(
              (sum, value) => sum + value,
              0
            )
          : null
      });
    }
  }

  if (!result.length) {
    throw new Error(
      "找不到可出租總倉位與已出租倉位的月度資料"
    );
  }

  return result.sort((a, b) =>
    a.month.localeCompare(b.month)
  );
}
