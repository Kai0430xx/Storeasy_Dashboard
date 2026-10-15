export const activityCategories=[
 '優惠倉','單店活動','官網活動','開幕優惠'
];
export function activityMatches(activity,category){
 return category==='all'
  ||(activity.category||'未分類')===category;
}
