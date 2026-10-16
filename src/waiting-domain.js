export const waitingStatuses = ['waiting','rented','cancelled'];

export function waitingInput(raw) {
  const text = (key, max, required=false) => {
    const value = String(raw[key] ?? '').trim();
    if ((required && !value) || value.length > max) {
      throw new Error(`${key === 'name' ? '姓名' : key === 'items' ? '存放物品' : key}未填寫或過長`);
    }
    return value;
  };

  const number = key => {
    if (raw[key] == null || String(raw[key]).trim() === '') return null;
    const n = Number(raw[key]);
    if (!Number.isFinite(n) || n < 0 || n > 100000000) {
      throw new Error('需求範圍請輸入有效的非負數字');
    }
    return n;
  };

  const phone=text('phone',4);
  const email=text('email',254);
  const needed=text('needed',5);

  if (phone && !/^\d{1,4}$/.test(phone)) {
    throw new Error('電話只能輸入前四碼，最多 4 位數字');
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error('Email 格式不正確');
  }
  if (needed) {
    const m=needed.match(/^(\d{2})\/(\d{2})$/);
    if (
      !m || +m[1]<1 || +m[1]>12 || +m[2]<1 ||
      +m[2]>[31,29,31,30,31,30,31,31,30,31,30,31][+m[1]-1]
    ) {
      throw new Error('需求時間請輸入有效的 MM/DD');
    }
  }

  const date=text('date',10,true);
  if (
    !/^20\d{2}-\d{2}-\d{2}$/.test(date) ||
    new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date
  ) {
    throw new Error('登記日期不正確');
  }

  const branchIds=[...new Set(raw.branchIds || [])];
  if (
    branchIds.length>100 ||
    branchIds.some(id=>typeof id!=='string'||!id||id.includes('/'))
  ) {
    throw new Error('候補據點不正確');
  }

  const otherBranches=text('otherBranches',300);
  if (!branchIds.length&&!otherBranches) {
    throw new Error('請選擇候補據點，或填寫其它據點');
  }

  const result={
    date,
    name:text('name',80,true),
    phone,
    email,
    needed,
    items:text('items',500,true),
    note:text('note',1000),
    branchIds,
    otherBranches,
    volumeMin:number('volumeMin'),
    volumeMax:number('volumeMax'),
    priceMin:number('priceMin'),
    priceMax:number('priceMax'),
    status:raw.status || 'waiting'
  };

  if (!waitingStatuses.includes(result.status)) {
    throw new Error('候補狀態不正確');
  }
  for(const [lo,hi]of[
    ['volumeMin','volumeMax'],
    ['priceMin','priceMax']
  ]) {
    if(result[lo]!==null&&result[hi]!==null&&result[lo]>result[hi]) {
      throw new Error('需求範圍下限不可大於上限');
    }
  }
  return result;
}

export function matchingVacancies(row, vacancies) {
  if(row.status!=='waiting') return [];
  return vacancies.filter(u=>
    row.branchIds.includes(u.branchId)&&
    ['volume','price'].every(k=>{
      const n=u[k], min=row[k+'Min'], max=row[k+'Max'];
      return typeof n==='number'&&Number.isFinite(n)&&
        (min==null||n>=min)&&(max==null||n<=max);
    })
  );
}

export function vacancyKey(u) {
  return JSON.stringify([
    u.branchId,u.code,u.vacantSince,u.lastEventId,u.lastEventDate
  ]);
}
