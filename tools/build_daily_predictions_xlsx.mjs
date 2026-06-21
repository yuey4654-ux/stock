import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const csvPath = path.join(root, "prediction_tracking", "daily_predictions.csv");
const outputDir = path.join(root, "outputs", "prediction_tracking");
const outputPath = path.join(outputDir, "daily_predictions_clean_2026-06-18.xlsx");

const csvTextRaw = await fs.readFile(csvPath, "utf8");
const csvText = csvTextRaw.replace(/^\uFEFF/, "").trim();
const rows = csvText.split(/\r?\n/).map((line) => line.split(","));
const [headers, ...bodyRows] = rows;
const parsedRows = bodyRows.map((row) => {
  const out = [...row];
  out[2] = Number(out[2]);
  out[3] = String(out[3]).padStart(/^\d+$/.test(String(out[3])) ? 6 : String(out[3]).length, "0");
  out[10] = Number(out[10]);
  out[11] = Number(String(out[11]).replace("%", "")) / 100;
  return out;
});

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("daily_predictions");
sheet.getRange("A1:P1").values = [headers];
sheet.getRange(`A2:P${parsedRows.length + 1}`).values = parsedRows;
sheet.getRange(`D2:D${parsedRows.length + 1}`).formulas = parsedRows.map((row) => {
  const code = String(row[3]);
  if (/^\d{6}$/.test(code)) {
    return [`=TEXT(${Number(code)},"000000")`];
  }
  return [`="${code.replace(/"/g, '""')}"`];
});

sheet.freezePanes.freezeRows(1);
sheet.getRange("A1:P1").format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF" },
};
const lastRow = parsedRows.length + 1;
sheet.getRange(`A1:P${lastRow}`).format.borders = {
  preset: "all",
  style: "thin",
  color: "#D9E2F3",
};
sheet.getRange(`A1:P${lastRow}`).format.font = { name: "Microsoft YaHei", size: 10 };
sheet.getRange(`A2:B${lastRow}`).format.numberFormat = "@";
sheet.getRange(`D2:D${lastRow}`).format.numberFormat = "@";
sheet.getRange(`K2:K${lastRow}`).setNumberFormat("0.00");
sheet.getRange(`L2:L${lastRow}`).setNumberFormat("0.00%");

sheet.getRange("A:A").format.columnWidthPx = 95;
sheet.getRange("B:B").format.columnWidthPx = 95;
sheet.getRange("C:C").format.columnWidthPx = 50;
sheet.getRange("D:D").format.columnWidthPx = 90;
sheet.getRange("E:E").format.columnWidthPx = 120;
sheet.getRange("F:F").format.columnWidthPx = 70;
sheet.getRange("G:G").format.columnWidthPx = 95;
sheet.getRange("H:H").format.columnWidthPx = 260;
sheet.getRange("I:I").format.columnWidthPx = 260;
sheet.getRange("J:J").format.columnWidthPx = 240;
sheet.getRange("K:K").format.columnWidthPx = 85;
sheet.getRange("L:L").format.columnWidthPx = 85;
sheet.getRange("M:N").format.columnWidthPx = 70;
sheet.getRange("O:O").format.columnWidthPx = 90;
sheet.getRange("P:P").format.columnWidthPx = 420;
sheet.getRange(`H2:J${lastRow}`).format.wrapText = true;
sheet.getRange(`P2:P${lastRow}`).format.wrapText = true;
sheet.getRange(`A1:P${lastRow}`).format.verticalAlignment = "top";
sheet.getRange("A1:P1").format.horizontalAlignment = "center";
sheet.getRange(`K2:L${lastRow}`).format.horizontalAlignment = "right";
sheet.getRange(`M2:O${lastRow}`).format.horizontalAlignment = "center";

sheet.getRange(`O2:O${lastRow}`).conditionalFormats.add("containsText", {
  text: "命中",
  format: { fill: "#E2F0D9", font: { color: "#006100", bold: true } },
});
sheet.getRange(`O2:O${lastRow}`).conditionalFormats.add("containsText", {
  text: "部分命中",
  format: { fill: "#FFF2CC", font: { color: "#7F6000", bold: true } },
});
sheet.getRange(`O2:O${lastRow}`).conditionalFormats.add("containsText", {
  text: "未命中",
  format: { fill: "#FCE4D6", font: { color: "#9C0006", bold: true } },
});
sheet.tables.add(`A1:P${lastRow}`, true, "DailyPredictionsTable");

const preview = await workbook.render({
  sheetName: "daily_predictions",
  range: "A1:P20",
  scale: 1,
  format: "png",
});
await fs.mkdir(outputDir, { recursive: true });
await fs.writeFile(
  path.join(outputDir, "daily_predictions_clean_2026-06-18_preview.png"),
  new Uint8Array(await preview.arrayBuffer()),
);

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);
console.log(outputPath);
