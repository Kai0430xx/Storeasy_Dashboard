export function operatingMonths(year, branch = {}) {
  const opening = String(branch.openingMonth || '');
  const valid = /^20\d{2}-(0[1-9]|1[0-2])$/.test(opening);
  const openingYear = valid ? Number(opening.slice(0,4)) : null;
  const startMonth = openingYear == null || Number(year)>openingYear ? 1
    : Number(year)<openingYear ? 13 : Number(opening.slice(5,7));
  return {startMonth,totalMonths:Math.max(0,13-startMonth)};
}
