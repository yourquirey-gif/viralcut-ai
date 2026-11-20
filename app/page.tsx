"use client";
import { useState } from "react";
import { Activity, ArrowUpRight, Bell, Check, ChevronDown, CircleHelp, Clapperboard, Clock3, Film, FolderOpen, LayoutDashboard, Link2, Plus, Radio, Search, Settings2, ShieldCheck, Sparkles, UploadCloud, WandSparkles, X, Zap } from "lucide-react";

type Page = "Overview" | "Projects" | "Live clipping" | "Clip library" | "Publishing" | "Settings";
const items: {name:Page; icon:typeof LayoutDashboard; group:string}[] = [
 {name:"Overview",icon:LayoutDashboard,group:"WORKSPACE"},{name:"Projects",icon:FolderOpen,group:"WORKSPACE"},
 {name:"Live clipping",icon:Radio,group:"CREATE"},{name:"Clip library",icon:Film,group:"CREATE"},
 {name:"Publishing",icon:UploadCloud,group:"MANAGE"},{name:"Settings",icon:Settings2,group:"MANAGE"}
];
function validYouTubeUrl(value:string) {
 try { const u=new URL(value.trim()); const host=u.hostname.toLowerCase().replace(/^www\\./,"").replace(/^m\\./,"");
 return host==="youtu.be" ? u.pathname.length>1 : host==="youtube.com" && (u.pathname==="/watch" || u.pathname.startsWith("/live/") || u.pathname.startsWith("/embed/")); } catch { return false; }
}
export default function Home() {
 const [page,setPage]=useState<Page>("Overview"),[url,setUrl]=useState(""),[error,setError]=useState(""),[modal,setModal]=useState(false),[toast,setToast]=useState(""),[filter,setFilter]=useState("");
 function continueWithUrl(){ if(!url.trim()){setError("Paste a YouTube Live URL to continue.");return;} if(!validYouTubeUrl(url)){setError("Enter a valid YouTube video or live URL.");return;} setError("");setModal(true); }
 const notify=(s:string)=>setToast(s);
 return <main className="shell">
  <aside className="sidebar">
   <div className="brand"><div className="brand-icon"><Clapperboard size={19}/></div><div><b>viralcut<span>.</span></b><small>CREATOR STUDIO</small></div></div>
   <button className="workspace"><span className="workspace-logo">VC</span><span><b>Personal workspace</b><small>Free workspace</small></span><ChevronDown size={15}/></button>
   <div className="searchbox"><Search size={15}/><input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Quick find"/><kbd>⌘ K</kbd></div>
   <nav>{["WORKSPACE","CREATE","MANAGE"].map(group=><div className="navgroup" key={group}><label>{group}</label>{items.filter(i=>i.group===group && i.name.toLowerCase().includes(filter.toLowerCase())).map(i=>{const Icon=i.icon;return <button key={i.name} className={"navitem "+(page===i.name?"selected":"")} onClick={()=>setPage(i.name)}><Icon size={17}/>{i.name}{i.name==="Live clipping"&&<i className="live-dot"/>}</button>})}</div>)}</nav>
   <div className="sidebar-bottom"><div className="engine-box"><div className="engine-head"><i/> <b>Local engine</b><span>Offline</span></div><p>Connect your desktop engine to capture and process streams.</p><button onClick={()=>notify("The local processing agent will be added in the next milestone.")}>Engine setup <ArrowUpRight size={13}/></button></div><button className="help" onClick={()=>notify("Help centre will be available in the public beta.")}><CircleHelp size={16}/> Help & support</button><div className="account"><div>A</div><span><b>Creator account</b><small>Personal plan</small></span></div></div>
  </aside>
  <section className="main">
   <header className="topbar"><div className="crumb">Workspace <span>/</span> <b>{page}</b></div><div className="topright"><div className="system"><i/> All systems normal</div><button className="iconbtn" onClick={()=>notify("You're all caught up.")}><Bell size={17}/></button><div className="user">A</div></div></header>
   <div className="content">
    <div className="welcome"><div><label>THURSDAY, NOVEMBER 20, 2026</label><h1>{page==="Overview"?"Your studio, at a glance.":page}</h1><p>{page==="Overview"?"Bring a livestream. Leave with moments worth sharing.":"Your "+page.toLowerCase()+" workspace."}</p></div><button className="primary" onClick={()=>setPage("Live clipping")}><Plus size={16}/> New live project</button></div>
    {page==="Overview"&&<>
     <div className="stats">{[{name:"Projects created",value:"0",foot:"Your projects will show up here",icon:FolderOpen},{name:"Clips generated",value:"0",foot:"No clips generated yet",icon:Clapperboard},{name:"Processing time",value:"—",foot:"Tracked after your first session",icon:Clock3},{name:"Publishing queue",value:"0",foot:"Nothing waiting to publish",icon:UploadCloud}].map(s=>{const Icon=s.icon;return <div className="stat" key={s.name}><div>{s.name}<Icon size={16}/></div><strong>{s.value}</strong><small>{s.foot}</small></div>})}</div>
    </>}
    {page==="Overview"||page==="Live clipping"?<>
     <div className="section-title"><div><h2>{page==="Overview"?"Start with a livestream":"Connect a YouTube livestream"}</h2><p>Paste a YouTube Live link to create your clipping project.</p></div><b>01 <span>/ 03</span></b></div>
     <div className="start-card"><div className="start-head"><div className="radio-icon"><Radio size={20}/></div><div><b>New live clipping session</b><p>ViralCut watches the stream, finds standout moments and prepares vertical clips for review.</p></div><span className="source"><i/> YOUTUBE LIVE</span></div>
      <div className="urlrow"><div className="urlfield"><Link2 size={17}/><input value={url} onChange={e=>{setUrl(e.target.value);setError("");}} onKeyDown={e=>e.key==="Enter"&&continueWithUrl()} placeholder="https://www.youtube.com/watch?v=..."/></div><button className="primary" onClick={continueWithUrl}>Continue <ArrowUpRight size={16}/></button></div>
      {error&&<div className="error"><X size={13}/>{error}</div>}
      <div className="card-foot"><span><ShieldCheck size={14}/> YouTube Live URLs only</span><span>Capture runs through your local processing engine</span><button onClick={()=>notify("Only record and publish livestreams you have permission to use. A public URL does not grant rights.")}>Usage & permissions <ArrowUpRight size={12}/></button></div>
     </div>
     <div className="columns"><div className="panel"><div className="panel-head"><div><h2>Recent projects</h2><p>Your latest clipping sessions</p></div><button onClick={()=>setPage("Projects")}>View all <ArrowUpRight size={14}/></button></div><div className="empty"><div><Film size={23}/></div><b>No projects yet</b><span>Your live clipping projects will appear here.</span><button className="secondary" onClick={()=>setPage("Live clipping")}><Plus size={14}/> Create first project</button></div></div>
     <div className="panel"><div className="panel-head"><div><h2>Activity</h2><p>What's happening in your studio</p></div><Activity size={17}/></div><div className="activity-empty"><div><Zap size={16}/></div><section><b>It's quiet in here</b><span>Real processing events will appear as they happen.</span></section></div></div></div>
     <div className="workflow"><div><Sparkles size={15}/> YOUR WORKFLOW</div><section><article><i>1</i><b>Connect a stream</b><small>Paste a YouTube Live URL</small></article><hr/><article><i>2</i><b>Find the moments</b><small>AI detects highlights live</small></article><hr/><article><i>3</i><b>Review & publish</b><small>Approve clips before sharing</small></article></section></div>
    </>:<div className="placeholder"><div><WandSparkles size={22}/></div><h2>{page==="Settings"?"Make ViralCut yours":"Your "+page.toLowerCase()+" will live here"}</h2><p>{page==="Settings"?"Preferences, connected accounts, engine settings and publishing defaults will be organised here.":"This space will populate when you create and process your first live project."}</p><small>FOUNDATION IN PROGRESS</small></div>}
   </div>
  </section>
  {modal&&<div className="overlay" onMouseDown={e=>e.target===e.currentTarget&&setModal(false)}><div className="dialog"><button className="close" onClick={()=>setModal(false)}><X size={18}/></button><div className="dialog-icon"><Radio size={22}/></div><label>NEW CLIPPING SESSION</label><h2>Ready to connect your stream?</h2><p>Your URL format is valid. Capture can begin after the local processing engine is installed and connected.</p><div className="preview"><Link2 size={15}/><span>{url}</span><Check size={15}/></div><div className="requirements"><div><Check size={15}/> URL format validated <b>Ready</b></div><div><Clock3 size={15}/> Local engine connection <b className="pending">Not connected</b></div><div><Clock3 size={15}/> FFmpeg & yt-dlp availability <b className="pending">Not checked</b></div></div><footer><button className="secondary" onClick={()=>setModal(false)}>Back</button><button className="primary" onClick={()=>{setModal(false);notify("URL validated. Recording will be enabled when the local engine is connected.");}}>Save project setup <ArrowUpRight size={15}/></button></footer><small className="permission"><ShieldCheck size={14}/> Only process streams you are authorized to record and publish.</small></div></div>}
  {toast&&<div className="toast"><Check size={15}/>{toast}<button onClick={()=>setToast("")}><X size={15}/></button></div>}
 </main>;
}
