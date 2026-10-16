import './occupancy-chart.css';

function offset(month:string,n:number){
 const [y,m]=month.split('-').map(Number);
 return new Date(Date.UTC(y,m-1+n,1)).toISOString().slice(0,7);
}

export default function OccupancyChart({month,rateFor}:{
 month:string;
 rateFor:(m:string)=>number|null;
}){
 return (
  <div className="occupancy-chart-scroll">
   <div className="occupancy-chart" role="img"
    aria-label="最近六個月出租率與去年同期比較">
    {Array.from({length:6},(_,i)=>offset(month,i-5)).map(m=>
     <div className="occupancy-month" key={m}>
      <div className="occupancy-pair">
       {[m,offset(m,-12)].map((period,index)=>{
        const rate=rateFor(period);
        return (
         <div className="occupancy-series" key={period}
          title={`${period}：${rate===null?'無資料':rate.toFixed(1)+'%'}`}>
          <span>{rate===null?'無資料':rate.toFixed(1)+'%'}</span>
          <div className="occupancy-track">
           {rate!==null&&
            <div className={index?'occupancy-bar previous':'occupancy-bar current'}
             style={{height:Math.max(0,Math.min(100,rate))+'%'}}/>
           }
          </div>
         </div>
        );
       })}
      </div>
      <small>{m.slice(0,4)}/{m.slice(5)}</small>
     </div>
    )}
   </div>
  </div>
 );
}
