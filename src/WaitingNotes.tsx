import {useEffect,useState} from 'react';
import {collection,onSnapshot} from 'firebase/firestore';
import {db} from './firebase';
import {contactInput,contactTime} from './waiting-domain.js';
import {addWaitingNote} from './waiting-list';
type Row=Record<string,any>;
const labels:Row={phone:'電話',line:'Line',visit:'現場'};
export default function WaitingNotes({rowId,legacy='',drafts,onChange,disabled=false,onPendingChange}:{rowId?:string;legacy?:string;drafts?:Row[];onChange?:(notes:Row[])=>void;disabled?:boolean;onPendingChange?:(pending:boolean)=>void}){
 useEffect(()=>()=>onPendingChange?.(false),[onPendingChange]);
 const [notes,setNotes]=useState<Row[]>([]),[editor,setEditor]=useState<Row|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{onPendingChange?.(!!editor);},[!!editor,onPendingChange]);
 useEffect(()=>{setNotes([]);setError('');if(!rowId)return;return onSnapshot(collection(db,'waitingList',rowId,'notes'),s=>setNotes(s.docs.map(d=>({id:d.id,...d.data()}))),e=>setError(e.message));},[rowId]);
 async function add(){if(!editor||busy)return;setError('');try{const clean=contactInput(editor);if(onChange){if((drafts||[]).length>=30)throw new Error('每次最多新增 30 筆備註，請先儲存後再繼續新增');onChange([...(drafts||[]),{...clean,id:crypto.randomUUID()}]);}else if(rowId){setBusy(true);await addWaitingNote(rowId,clean);}setEditor(null);}catch(e:any){setError(e.message);}finally{setBusy(false);}}
 const entries=[...notes.map(n=>({...n,draftIndex:-1})),...(drafts||[]).map((n,i)=>({...n,draftIndex:i}))].sort((a:Row,b:Row)=>b.at.localeCompare(a.at)||(b.draftIndex>=0?Number.MAX_SAFE_INTEGER:b.createdAt?.toMillis?.()||0)-(a.draftIndex>=0?Number.MAX_SAFE_INTEGER:a.createdAt?.toMillis?.()||0)||(b.order||0)-(a.order||0)||String(a.id).localeCompare(String(b.id))) as Row[];
 return <section className="waiting-notes" aria-label="聯絡備註"><div className="waiting-notes-heading"><h3>備註</h3><button type="button" className="secondary" disabled={disabled||busy||!!editor} onClick={()=>{setEditor({at:contactTime(),channel:'phone',text:''});setError('');}}>新增備註</button></div>
  {editor&&<div className="waiting-note-editor"><div className="waiting-contact-fields"><label>備註時間<input type="datetime-local" value={editor.at} disabled={disabled||busy} onChange={e=>setEditor({...editor,at:e.target.value})}/></label><label>分類<select aria-label="分類" value={editor.channel} disabled={disabled||busy} onChange={e=>setEditor({...editor,channel:e.target.value})}>{Object.entries(labels).map(([key,value])=><option key={key} value={key}>{value}</option>)}</select></label><label>備註內容<textarea aria-label="備註內容" maxLength={2000} value={editor.text} disabled={disabled||busy} onChange={e=>setEditor({...editor,text:e.target.value})}/></label></div><div className="waiting-status-tabs"><button type="button" className="secondary" disabled={disabled||busy} onClick={add}>{onChange?'加入備註':'儲存備註'}</button><button type="button" className="text-button" disabled={disabled||busy} onClick={()=>setEditor(null)}>取消新增備註</button></div></div>}
  {entries.map(n=><article className={'waiting-note'+(n.draftIndex>=0?' draft':'')} key={n.id}><div><time>{n.at.replace('T',' ').replace(/-/g,'/')}</time><span className="badge">{labels[n.channel]}</span>{n.draftIndex>=0&&<><small>待儲存</small><button type="button" disabled={disabled} className="text-button danger" aria-label={'移除未儲存備註 '+(n.draftIndex+1)} onClick={()=>onChange?.((drafts||[]).filter((_,j)=>j!==n.draftIndex))}>移除</button></>}</div><p>{n.text}</p></article>)}
  {legacy&&<article className="waiting-note"><small>原有備註（未記錄聯絡時間）</small><p>{legacy}</p></article>}
  {!legacy&&!notes.length&&!drafts?.length&&!editor&&<p className="hint">尚無備註，可逐筆新增聯絡紀錄。</p>}
  {error&&<p role="alert" className="alert error">{error}</p>}{onChange&&drafts&&drafts.length>0&&<p className="hint">請按視窗底部「確認儲存」，一併保存這些備註。</p>}
 </section>;
}
