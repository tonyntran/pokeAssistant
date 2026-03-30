import { useState, useRef, useEffect, useCallback } from "react";
import {
  Search, Zap, Star, Plus, Bell, Heart, TrendingUp, TrendingDown,
  ChevronDown, ArrowDown, BarChart2, Grid, Package, User, List,
  X, Filter, Share2, ChevronLeft, Info, Minus, Lock, ChevronRight,
  AlertTriangle, Bookmark, Eye, Swords, LayoutGrid, BookOpen,
  TrendingUp as TrendIcon, Award, ShieldCheck, Layers
} from "lucide-react";

const _style = document.createElement("style");
_style.textContent = `@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}`;
document.head.appendChild(_style);

// ─── Constants & Data ────────────────────────────────────────────────────────

const CARDS = [
  { id:1,  name:"Mega Gengar ex",          set:"Ascended Heroes",                  num:"284/217", market:1150, psa10:3223, psa10pct:180, change:1.36,
    img:"https://images.pokemontcg.io/sv8/184_hires.png" },
  { id:2,  name:"Mega Charizard X ex",     set:"Phantasmal Flames",                num:"125/94",  market:850,  psa10:2134, psa10pct:151, change:65.84,
    img:"https://images.pokemontcg.io/sv6/125_hires.png" },
  { id:3,  name:"Pikachu ex",              set:"Ascended Heroes",                  num:"276/217", market:762,  psa10:2640, psa10pct:246, change:1.90,
    img:"https://images.pokemontcg.io/sv8/186_hires.png" },
  { id:4,  name:"Mega Dragonite ex",       set:"Ascended Heroes",                  num:"290/217", market:673,  psa10:2050, psa10pct:205, change:62.97,
    img:"https://images.pokemontcg.io/sv8/185_hires.png" },
  { id:5,  name:"Celebratory Fanfare",     set:"Mega Evolution Black Star Promos", num:"028",     market:540,  psa10:2389, psa10pct:342, change:-11.50,
    img:"https://images.pokemontcg.io/sv3pt5/191_hires.png" },
  { id:6,  name:"Team Rocket's Mewtwo ex", set:"Destined Rivals",                  num:"231",     market:530,  psa10:1224, psa10pct:131, change:22.42,
    img:"https://images.pokemontcg.io/sv9/131_hires.png" },
  { id:7,  name:"Umbreon ex",              set:"Prismatic Evolutions",             num:"181",     market:1395, psa10:4500, psa10pct:222, change:8.63,
    img:"https://images.pokemontcg.io/sv8pt5/161_hires.png" },
  { id:8,  name:"Sylveon ex",              set:"Prismatic Evolutions",             num:"155",     market:379,  psa10:1099, psa10pct:190, change:28.11,
    img:"https://images.pokemontcg.io/sv8pt5/155_hires.png" },
  { id:9,  name:"Leafeon ex",              set:"Prismatic Evolutions",             num:"144",     market:275,  psa10:644,  psa10pct:134, change:8.52,
    img:"https://images.pokemontcg.io/sv8pt5/144_hires.png" },
  { id:10, name:"Espeon ex",               set:"Prismatic Evolutions",             num:"165",     market:248,  psa10:911,  psa10pct:268, change:17.83,
    img:"https://images.pokemontcg.io/sv8pt5/165_hires.png" },
  { id:11, name:"Vaporeon ex",             set:"Prismatic Evolutions",             num:"149",     market:215,  psa10:883,  psa10pct:310, change:6.27,
    img:"https://images.pokemontcg.io/sv8pt5/149_hires.png" },
  { id:12, name:"Glaceon ex",              set:"Prismatic Evolutions",             num:"160",     market:200,  psa10:583,  psa10pct:191, change:17.25,
    img:"https://images.pokemontcg.io/sv8pt5/160_hires.png" },
];

const PRODUCTS = [
  { id:1,  name:"Mini Tin: Zorua & Cramorant",                 set:"Ascended Heroes",    market:20.74, change:-14.81, pullRate:"Good",
    img:"https://assets.tcgplayer.com/fit-in/437x437/product/3/3f/3f3e9e0a-89f4-4c09-b3c6-3e6a7e9e1234.jpg" },
  { id:2,  name:"Mini Tin: Clefairy & Chikorita",              set:"Ascended Heroes",    market:24.29, change:-5.48,  pullRate:"Good",
    img:"https://assets.tcgplayer.com/fit-in/437x437/product/3/5c/5c9e0a89-f44c-09b3-c63e-6a7e9e12345a.jpg" },
  { id:3,  name:"Mini Tin: Marill & Togetic",                  set:"Ascended Heroes",    market:18.99, change:-1.09,  pullRate:"Good",
    img:"https://assets.tcgplayer.com/fit-in/437x437/product/3/8b/8b3e9e0a-89f4-4c09-b3c6-3e6a7e9e9876.jpg" },
  { id:4,  name:"Booster Bundle",                              set:"Ascended Heroes",    market:71.00, change:2.07,   pullRate:"Good",
    img:"https://product-images.tcgplayer.com/fit-in/437x437/614985.jpg" },
  { id:5,  name:"Elite Trainer Box [Pokemon Center]",          set:"Ascended Heroes",    market:341,   change:3.04,   pullRate:"Good",
    img:"https://product-images.tcgplayer.com/fit-in/437x437/614986.jpg" },
  { id:6,  name:"Phantasmal Flames Booster Bundle",            set:"Phantasmal Flames",  market:48.93, change:-0.47,  pullRate:"Mid",
    img:"https://product-images.tcgplayer.com/fit-in/437x437/604827.jpg" },
  { id:7,  name:"Mega Charizard X Ex Ultra-Premium Collection",set:"Phantasmal Flames",  market:187,   change:40.64,  pullRate:"Good",
    img:"https://product-images.tcgplayer.com/fit-in/437x437/604826.jpg" },
  { id:8,  name:"Evolutions ETB [Mega Charizard Y]",           set:"Evolutions",         market:660,   change:89,     pullRate:"Garbage",
    img:"https://product-images.tcgplayer.com/fit-in/437x437/201246.jpg" },
];

const PRODUCT_CARDS_INSIDE = [
  { id:1, name:"Mega Charizard X ex", set:"Phantasmal Flames", num:"125/94", market:850,   psa10:2134, psa10pct:151, change:65.84,
    img:"https://images.pokemontcg.io/sv6/125_hires.png" },
  { id:2, name:"Mega Charizard X ex", set:"Phantasmal Flames", num:"130/94", market:400,   psa10:3000, psa10pct:650, change:-47.55,
    img:"https://images.pokemontcg.io/sv6/130_hires.png" },
  { id:3, name:"Mega Charizard X ex", set:"Phantasmal Flames", num:"109/94", market:44.99, psa10:222,  psa10pct:392, change:-0.01,
    img:"https://images.pokemontcg.io/sv6/109_hires.png" },
  { id:4, name:"Dawn",                set:"Phantasmal Flames", num:"129/94", market:37.99, psa10:161,  psa10pct:323, change:-1.99,
    img:"https://images.pokemontcg.io/sv6/129_hires.png" },
];

const SEARCH_SUGGESTIONS_CARDS = [
  { type:"set",  name:"ex Starter Set Pikachu ex & Pawmot",  sub:"Scarlet & Violet",                    price:null    },
  { type:"card", name:"Pikachu-EX",                          sub:"XY Black Star Promos #XY124",         price:"$7.6k" },
  { type:"card", name:"Pikachu-EX",                          sub:"Expansion Pack: 20th Anniversary #94",price:"$5.4k" },
  { type:"card", name:"Pikachu [Reverse Holo]",              sub:"Expedition #124",                     price:"$3.2k" },
  { type:"card", name:"Pikachu ex",                          sub:"Ascended Heroes #276/217",            price:"$2.6k" },
  { type:"card", name:"Pikachu ex",                          sub:"Prismatic Evolutions #033/082",       price:"$1.3k" },
];

const SEARCH_SUGGESTIONS_PRODUCTS = [
  { type:"set",  name:"Charizard VSTAR vs Rayquaza VMAX Special Deck Set", sub:"Sword & Shield",  price:null    },
  { type:"set",  name:"Venusaur, Charizard & Blastoise Special Deck Set ex",sub:"Scarlet & Violet",price:"$165"  },
  { type:"set",  name:"VMAX Starter Set 2 (Charizard)",                    sub:"Sword & Shield",  price:null    },
  { type:"card", name:"Charizard [1st Edition]",                           sub:"Base [1st Edition] #4",price:"$518.5k"},
  { type:"card", name:"Charizard ★ δ",                                     sub:"Dragon Frontiers #100", price:"$56.6k" },
  { type:"card", name:"Charizard",                                         sub:"Blastoise #142",        price:"$43.4k" },
];

const RAW_DATA    = [1100,1080,1050,1020,990,960,930,900,870,850,820,800,780,760,750,760,780,810,850,900,960,1020,1080,1150,1200,1280,1350,1395];
const PSA10_DATA  = RAW_DATA.map(v => Math.round(v * 3.22));
const PROD_DATA   = [42,44,43,45,46,44,43,42,44,46,45,47,46,44,43,42,44,46,48,47,46,47,48,49,48,47,48,49];

function generateDates(count) {
  const out=[], end=new Date("2026-03-26");
  for(let i=count-1;i>=0;i--){ const d=new Date(end); d.setDate(d.getDate()-i); out.push(d); }
  return out;
}
const CHART_DATES = generateDates(RAW_DATA.length);
function fmtDate(d){ return d.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}); }

const GRADING=[
  {grade:"PSA 10",pop:1842,pct:42,price:4500,trend:"up",  rate:"Good",   rc:"#4ade80"},
  {grade:"PSA 9", pop:1204,pct:27,price:1288,trend:"up",  rate:"Average",rc:"#eab308"},
  {grade:"PSA 8", pop:712, pct:16,price:820, trend:"flat",rate:"Average",rc:"#eab308"},
  {grade:"PSA 7", pop:389, pct:9, price:540, trend:"down",rate:"Poor",   rc:"#f87171"},
  {grade:"PSA 6", pop:193, pct:4, price:310, trend:"down",rate:"Garbage",rc:"#ef4444"},
  {grade:"PSA 5", pop:84,  pct:2, price:195, trend:"down",rate:"Garbage",rc:"#ef4444"},
];
const POP=[
  {grade:"PSA 10",count:1842,bar:100},
  {grade:"PSA 9", count:1204,bar:65 },
  {grade:"PSA 8", count:712, bar:39 },
  {grade:"PSA 7", count:389, bar:21 },
  {grade:"PSA 6", count:193, bar:10 },
  {grade:"PSA 5", count:84,  bar:5  },
];

// ─── Line Chart ───────────────────────────────────────────────────────────────

function LineChart({ data, dates, color="#4ade80" }) {
  const [hIdx,setHIdx]=useState(null);
  const svgRef=useRef(null);
  const W=500,H=160,pad={top:10,right:10,bottom:30,left:10};
  const minV=Math.min(...data)*0.97,maxV=Math.max(...data)*1.02,n=data.length;
  const gx=i=>pad.left+(i/(n-1))*(W-pad.left-pad.right);
  const gy=v=>pad.top+(1-(v-minV)/(maxV-minV))*(H-pad.top-pad.bottom);
  const pts=data.map((v,i)=>`${gx(i)},${gy(v)}`).join(" ");
  const area=`${gx(0)},${H-pad.bottom} ${pts} ${gx(n-1)},${H-pad.bottom}`;
  const axisIdxs=[0,7,14,21,27];
  const onMove=e=>{
    const r=svgRef.current.getBoundingClientRect();
    const x=(e.clientX-r.left)*(W/r.width);
    setHIdx(Math.max(0,Math.min(n-1,Math.round(((x-pad.left)/(W-pad.left-pad.right))*(n-1)))));
  };
  const hx=hIdx!==null?gx(hIdx):null;
  const hy=hIdx!==null?gy(data[hIdx]):null;
  const tx=hx!==null?Math.min(hx-48,W-112):0;
  const gradId=`cg-${color.replace("#","")}`;
  return (
    <svg ref={svgRef} width="100%" viewBox={`0 0 ${W} ${H}`}
      onMouseMove={onMove} onMouseLeave={()=>setHIdx(null)} style={{cursor:"crosshair"}}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${gradId})`}/>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      {axisIdxs.map((ai,i)=>(
        <text key={i} x={gx(ai)} y={H-6} fontSize="9" fill="#4b5563"
          textAnchor={i===0?"start":i===axisIdxs.length-1?"end":"middle"}>
          {dates&&dates[ai]?dates[ai].toLocaleDateString("en-US",{month:"short",day:"numeric"})+" '"+String(dates[ai].getFullYear()).slice(2):`Day ${ai}`}
        </text>
      ))}
      {hIdx!==null&&<>
        <line x1={hx} y1={pad.top} x2={hx} y2={H-pad.bottom} stroke="#6b7280" strokeWidth="1" strokeDasharray="4 3"/>
        <circle cx={hx} cy={hy} r="4" fill={color} stroke="#000" strokeWidth="1.5"/>
        <rect x={tx} y={hy-38} width="106" height="30" rx="5" fill="#1f1f1f" stroke="#374151" strokeWidth="0.5"/>
        <text x={tx+8} y={hy-24} fontSize="9.5" fill="#9ca3af">{dates&&dates[hIdx]?fmtDate(dates[hIdx]):"—"}</text>
        <text x={tx+8} y={hy-11} fontSize="11" fontWeight="500" fill="#fff">${data[hIdx].toLocaleString()}</text>
      </>}
    </svg>
  );
}

// ─── Buy Signal Gauge ────────────────────────────────────────────────────────

function BuySignalGauge({value=35}){
  const W=340,H=62,bH=18,bY=8,ix=(value/100)*W;
  const labels=["STRONG SELL","SELL","HOLD","BUY","STRONG BUY"];
  return(
    <svg width="100%" viewBox={`0 0 ${W} ${H}`}>
      <defs>
        <linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#ef4444"/><stop offset="25%" stopColor="#f97316"/>
          <stop offset="50%" stopColor="#eab308"/><stop offset="75%" stopColor="#84cc16"/>
          <stop offset="100%" stopColor="#22c55e"/>
        </linearGradient>
        <filter id="ds"><feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.5"/></filter>
      </defs>
      <rect x="0" y={bY} width={W} height={bH} rx={bH/2} fill="url(#gg)"/>
      <circle cx={ix} cy={bY+bH/2} r="9" fill="white" filter="url(#ds)"/>
      {labels.map((l,i)=>(
        <text key={i} x={(i/(labels.length-1))*W} y={H-4} fontSize="7.5" fill="#6b7280" textAnchor="middle">{l}</text>
      ))}
    </svg>
  );
}

// ─── 3D Tilt Card ────────────────────────────────────────────────────────────

function TiltCard({children,className=""}){
  const ref=useRef(null);
  const [tilt,setTilt]=useState({x:0,y:0,active:false});
  const onMove=e=>{
    const r=ref.current.getBoundingClientRect();
    const x=((e.clientX-r.left)/r.width-0.5)*14;
    const y=-((e.clientY-r.top)/r.height-0.5)*14;
    setTilt({x,y,active:true});
  };
  const onLeave=()=>setTilt({x:0,y:0,active:false});
  return(
    <div ref={ref} className={className}
      onMouseMove={onMove} onMouseLeave={onLeave}
      style={{
        transform:tilt.active?`perspective(700px) rotateY(${tilt.x}deg) rotateX(${tilt.y}deg) scale(1.03)`:"perspective(700px) rotateY(0deg) rotateX(0deg) scale(1)",
        transition:tilt.active?"transform 0.05s linear":"transform 0.35s ease",
        transformStyle:"preserve-3d",
      }}>
      {children}
    </div>
  );
}

// ─── Grading Breakdown ────────────────────────────────────────────────────────

function GradingBreakdown(){
  return(
    <div className="mt-6 rounded-xl border border-gray-800 overflow-hidden" style={{background:"#0f0f0f"}}>
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <span className="text-white text-sm font-semibold">Grading Breakdown</span>
        <span className="text-xs text-gray-500">Total graded: 4,424</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[540px]">
          <thead>
            <tr className="border-b border-gray-800">
              {["GRADE","POPULATION","%","MARKET PRICE","TREND","PULL RATE"].map(h=>(
                <th key={h} className="px-4 py-2 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {GRADING.map((r,i)=>(
              <tr key={i} className="border-b border-gray-900 hover:bg-gray-900/50 transition-colors">
                <td className="px-4 py-3 font-semibold text-white">{r.grade}</td>
                <td className="px-4 py-3 text-gray-300">{r.pop.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{width:`${r.pct}%`}}/>
                    </div>
                    <span className="text-gray-400 text-xs">{r.pct}%</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-white font-medium">${r.price.toLocaleString()}</td>
                <td className="px-4 py-3">
                  {r.trend==="up"&&<TrendingUp size={14} className="text-green-400"/>}
                  {r.trend==="down"&&<TrendingDown size={14} className="text-red-400"/>}
                  {r.trend==="flat"&&<span className="text-gray-500 text-xs">—</span>}
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full"
                    style={{color:r.rc,background:r.rc+"22"}}>{r.rate}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Population Report ────────────────────────────────────────────────────────

function PopulationReport(){
  return(
    <div className="mt-4 rounded-xl border border-gray-800 overflow-hidden" style={{background:"#0f0f0f"}}>
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <span className="text-white text-sm font-semibold">Population Report</span>
        <span className="text-xs text-gray-500">PSA Registry</span>
      </div>
      <div className="px-4 py-4 space-y-3">
        {POP.map((r,i)=>(
          <div key={i} className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-12 text-right flex-shrink-0">{r.grade}</span>
            <div className="flex-1 h-5 bg-gray-900 rounded-full overflow-hidden">
              <div className="h-full rounded-full flex items-center pl-2 transition-all duration-700"
                style={{width:`${r.bar}%`,background:i===0?"linear-gradient(90deg,#4f46e5,#818cf8)":"linear-gradient(90deg,#374151,#6b7280)"}}>
                {r.bar>15&&<span className="text-xs text-white font-medium">{r.count.toLocaleString()}</span>}
              </div>
            </div>
            {r.bar<=15&&<span className="text-xs text-gray-400 w-10">{r.count.toLocaleString()}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Pull Calculator ──────────────────────────────────────────────────────────

function PullCalculator(){
  const [packs,setPacks]=useState(36);
  const odds=1441.44, chance=(1-Math.pow(1-1/odds,packs))*100, cost=Math.round(packs*4.5);
  return(
    <div className="mt-4 rounded-xl border border-gray-800" style={{background:"#0f0f0f"}}>
      <div className="p-4 border-b border-gray-800 flex items-start justify-between">
        <div>
          <div className="text-sm font-semibold text-white">Pull Calculator</div>
          <div className="text-xs text-gray-500 mt-0.5">See your odds of pulling this card based on packs opened</div>
        </div>
        <span className="text-xs text-gray-500 mt-0.5">1 IN {Math.round(odds).toLocaleString()}</span>
      </div>
      {chance<10&&(
        <div className="mx-4 mt-4 flex items-center gap-2 rounded-lg px-3 py-2.5" style={{background:"#2d0a0a",border:"1px solid #7f1d1d"}}>
          <AlertTriangle size={14} className="text-red-400 flex-shrink-0"/>
          <span className="text-red-400 text-xs font-medium">The odds aren't in your favor.</span>
        </div>
      )}
      <div className="p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-gray-400">Packs opened</span>
          <div className="flex items-center gap-1 rounded-lg border border-gray-700 px-2 py-1" style={{background:"#1a1a1a"}}>
            <button onClick={()=>setPacks(p=>Math.max(1,p-1))} className="text-gray-400 hover:text-white w-5 h-5 flex items-center justify-center transition-colors"><Minus size={11}/></button>
            <span className="text-white text-sm font-medium w-8 text-center">{packs}</span>
            <button onClick={()=>setPacks(p=>p+1)} className="text-gray-400 hover:text-white w-5 h-5 flex items-center justify-center transition-colors"><Plus size={11}/></button>
          </div>
          <span className="text-xs text-red-400">-${cost}</span>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="text-xs text-gray-500">Chance</span>
            <Info size={11} className="text-gray-600"/>
            <span className="text-white text-sm font-semibold">{chance.toFixed(1)}%</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-4">
          {[{label:"50% CHANCE",dot:"#eab308",packs:"999 packs",cost:"~$9,491"},{label:"90% CHANCE",dot:"#4ade80",packs:"3,318 packs",cost:"~$31,521"}].map((c,i)=>(
            <div key={i} className="rounded-lg p-3 border border-gray-800" style={{background:"#1a1a1a"}}>
              <div className="flex items-center gap-1.5 mb-1.5"><div className="w-2 h-2 rounded-full" style={{background:c.dot}}/><span className="text-xs text-gray-400">{c.label}</span></div>
              <div className="text-white font-semibold text-sm">{c.packs}</div>
              <div className="text-red-400 text-xs mt-0.5">{c.cost}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-300" style={{width:`${Math.min(chance*5,100)}%`,background:"linear-gradient(90deg,#4ade80,#22c55e)"}}/>
        </div>
        <div className="flex justify-between text-xs text-gray-600 mt-1"><span>0%</span><span>50%</span><span>100%</span></div>
      </div>
    </div>
  );
}

// ─── Rip vs Flip ─────────────────────────────────────────────────────────────

function RipVsFlip({compact=false}){
  return(
    <div className={`rounded-xl border ${compact?"border-red-900/50":"border-gray-800"}`} style={{background:compact?"#1a0808":"#0f0f0f"}}>
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {compact&&<div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{background:"#991b1b"}}><Lock size={12} className="text-red-400"/></div>}
          <span className="text-white text-sm font-semibold">RIP VS FLIP</span>
          {compact&&<Info size={12} className="text-gray-600"/>}
          {compact&&<span className="text-xs text-gray-500 ml-1">Keep it closed</span>}
        </div>
        <span className="text-xs font-bold px-2 py-0.5 rounded" style={{background:"#450a0a",color:"#f87171"}}>HOLD SEALED</span>
      </div>
      {compact?(
        <div className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="flex-1 h-2 rounded-full overflow-hidden bg-gray-800">
              <div className="h-full rounded-full" style={{width:"47%",background:"linear-gradient(90deg,#ef4444,#f97316)"}}/>
            </div>
            <div className="w-1 h-2 bg-gray-600 rounded-full"/>
            <div className="flex-1 h-2 rounded-full overflow-hidden bg-gray-800">
              <div className="h-full rounded-full" style={{width:"20%",background:"#374151"}}/>
            </div>
          </div>
          <span className="text-white text-2xl font-bold">47%</span>
          <span className="text-gray-400 text-sm ml-2">EV / Market</span>
        </div>
      ):(
        <div className="p-4 grid grid-cols-3 gap-4">
          {[{label:"EV / Pack Price",value:"47%",sub:"Expected value ratio"},{label:"Break-even Odds",value:"2.5%",sub:"Chance to profit opening"},{label:"Sealed Premium",value:"+18%",sub:"vs. singles market"}].map((s,i)=>(
            <div key={i}><div className="text-white text-xl font-bold">{s.value}</div><div className="text-gray-400 text-xs mt-0.5">{s.label}</div><div className="text-gray-600 text-xs">{s.sub}</div></div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Market Sentiment ─────────────────────────────────────────────────────────

const SENTIMENT_DATA = {
  score: 72,          // 0-100 bullish score
  label: "Bullish",
  sources: [
    { platform:"Reddit r/pkmntcg",    mentions:143, sentiment:"positive", delta:"+28% vs last week",  excerpt:"\"Umbreon ex demand is insane rn, people are sleeping on it\"" },
    { platform:"Twitter / X",         mentions:89,  sentiment:"positive", delta:"+41% vs last week",  excerpt:"\"Just pulled an Umbreon ex IR — these are going to the moon 🚀\"" },
    { platform:"eBay Sold Listings",  mentions:null, sentiment:"positive", delta:"4.1 sales/day avg", excerpt:"Consistent sell-through rate, no sign of market saturation" },
    { platform:"TCGPlayer Forums",    mentions:34,  sentiment:"neutral",  delta:"Stable",             excerpt:"\"Fair price, wouldn't overpay but it's not going anywhere\"" },
    { platform:"YouTube Comments",    mentions:22,  sentiment:"positive", delta:"+15% vs last week",  excerpt:"\"This card is in every top 10 wishlist video right now\"" },
  ],
  keywords: ["undervalued","grail","must-have","rising","hype","alt art"],
  summary: "Community sentiment is strongly bullish driven by sustained collector demand and low raw supply. Social volume has accelerated 34% week-over-week. eBay velocity is healthy at 4.1 sales/day with no price suppression. Primary risk is a broader market cooldown.",
};

const SENT_COLOR = { positive:"#4ade80", neutral:"#eab308", negative:"#f87171" };
const SENT_BG    = { positive:"rgba(74,222,128,0.1)", neutral:"rgba(234,179,8,0.1)", negative:"rgba(248,113,113,0.1)" };

function MarketSentiment({ card }) {
  const [expanded, setExpanded] = useState(false);
  const s = SENTIMENT_DATA;
  const arc = (v) => {
    const r=44, cx=60, cy=60, start=-Math.PI*0.75, end=start+(v/100)*Math.PI*1.5;
    const x1=cx+r*Math.cos(start), y1=cy+r*Math.sin(start);
    const x2=cx+r*Math.cos(end),   y2=cy+r*Math.sin(end);
    const large=v>66?1:0;
    return `M${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2}`;
  };
  const needleAngle = -135 + (s.score/100)*270;
  const needleRad = (needleAngle*Math.PI)/180;
  const nx = 60 + 34*Math.cos(needleRad), ny = 60 + 34*Math.sin(needleRad);

  return (
    <div className="rounded-xl border border-gray-800 mb-3 overflow-hidden" style={{background:"#0f0f0f"}}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded flex items-center justify-center" style={{background:"linear-gradient(135deg,#6366f1,#a855f7)"}}>
            <TrendingUp size={11} className="text-white"/>
          </div>
          <span className="text-white text-sm font-semibold">Market Sentiment</span>
          <Info size={12} className="text-gray-600"/>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{background:"rgba(74,222,128,0.15)",color:"#4ade80"}}>
            {s.label}
          </span>
          <span className="text-xs text-gray-500">Live</span>
          <div className="w-1.5 h-1.5 rounded-full bg-green-400" style={{animation:"pulse 2s infinite"}}/>
        </div>
      </div>

      <div className="p-4">
        {/* Score gauge + summary row */}
        <div className="flex gap-4 mb-4">
          {/* Gauge */}
          <div className="flex-shrink-0">
            <svg width="120" height="72" viewBox="0 0 120 72">
              {/* Track */}
              <path d={arc(100)} fill="none" stroke="#1f2937" strokeWidth="8" strokeLinecap="round"/>
              {/* Fill - color shifts red→yellow→green */}
              <path d={arc(s.score)} fill="none" strokeWidth="8" strokeLinecap="round"
                stroke={s.score>65?"#4ade80":s.score>40?"#eab308":"#f87171"}/>
              {/* Needle */}
              <line x1="60" y1="60" x2={nx} y2={ny} stroke="white" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="60" cy="60" r="3.5" fill="white"/>
              {/* Score text */}
              <text x="60" y="56" textAnchor="middle" fontSize="15" fontWeight="700" fill="white">{s.score}</text>
              <text x="60" y="68" textAnchor="middle" fontSize="8" fill="#6b7280">/ 100</text>
            </svg>
            <div className="flex justify-between text-xs text-gray-600 mt-0.5" style={{width:120}}>
              <span>Bear</span><span>Bull</span>
            </div>
          </div>

          {/* Summary */}
          <div className="flex-1 min-w-0">
            <p className="text-gray-300 text-xs leading-relaxed">{s.summary}</p>
            {/* Keywords */}
            <div className="flex flex-wrap gap-1 mt-2">
              {s.keywords.map(k=>(
                <span key={k} className="text-xs px-2 py-0.5 rounded-full"
                  style={{background:"rgba(99,102,241,0.15)",color:"#818cf8"}}>
                  #{k}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Source breakdown */}
        <div className="space-y-2">
          {(expanded ? s.sources : s.sources.slice(0,3)).map((src,i)=>(
            <div key={i} className="rounded-lg p-3 border border-gray-800/60" style={{background:"#111"}}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full" style={{background:SENT_COLOR[src.sentiment]}}/>
                  <span className="text-white text-xs font-medium">{src.platform}</span>
                  {src.mentions&&<span className="text-gray-600 text-xs">{src.mentions} mentions</span>}
                </div>
                <span className="text-xs px-1.5 py-0.5 rounded" style={{background:SENT_BG[src.sentiment],color:SENT_COLOR[src.sentiment]}}>
                  {src.delta}
                </span>
              </div>
              <p className="text-gray-500 text-xs italic leading-relaxed">{src.excerpt}</p>
            </div>
          ))}
        </div>

        {s.sources.length>3&&(
          <button onClick={()=>setExpanded(e=>!e)}
            className="mt-2 w-full text-xs text-gray-500 hover:text-gray-300 py-1.5 rounded-lg border border-gray-800 transition-colors"
            style={{background:"#111"}}>
            {expanded?`Show less ▲`:`Show ${s.sources.length-3} more sources ▼`}
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Card Detail View ─────────────────────────────────────────────────────────

function CardDetailView({card,onBack}){
  const [mode,setMode]=useState("Raw");
  const [period,setPeriod]=useState("1M");
  const [activeTab,setActiveTab]=useState("Grading");
  const headerRef=useRef(null),scrollRef=useRef(null);
  const data=mode==="Raw"?RAW_DATA:PSA10_DATA;
  const cur=data[data.length-1],chg=cur-data[0],chgP=((chg/data[0])*100).toFixed(1);
  useEffect(()=>{
    const el=scrollRef.current; if(!el)return; let last=0;
    const h=()=>{ const dir=el.scrollTop>last?"down":"up"; last=el.scrollTop; if(headerRef.current) headerRef.current.style.transform=(dir==="down"&&el.scrollTop>60)?"translateY(-100%)":"translateY(0)"; };
    el.addEventListener("scroll",h,{passive:true}); return()=>el.removeEventListener("scroll",h);
  },[]);
  return(
    <div className="min-h-screen flex flex-col" style={{background:"#000"}}>
      <div ref={headerRef} className="flex items-center justify-between px-4 py-3 border-b border-gray-900 sticky top-0 z-30" style={{background:"#080808",transition:"transform 0.3s ease"}}>
        <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors"><ChevronLeft size={20}/></button>
        <div className="flex items-center gap-2">
          <img src={card.img} alt={card.name} className="w-5 h-7 object-cover rounded" onError={e=>{e.target.src="https://placehold.co/28x40/1a1a2e/6366f1?text=?"}}/>
          <div><div className="text-white text-sm font-medium">{card.name}</div><div className="text-xs" style={{color:"#a78bfa"}}>{card.set}</div></div>
        </div>
        <button className="text-gray-400 hover:text-white transition-colors"><Share2 size={18}/></button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="lg:w-72 flex-shrink-0">
              <div className="lg:sticky lg:top-4">
                <div className="rounded-2xl overflow-hidden border border-gray-800 mb-4" style={{background:"linear-gradient(135deg,#0f0f1a,#1a0a2e)"}}>
                  <img src={card.img} alt={`${card.name} full art trading card holographic`} className="w-full object-cover" style={{maxHeight:320}} onError={e=>{e.target.src=`https://placehold.co/400x560/0a0a1a/6366f1?text=${encodeURIComponent(card.name)}`}}/>
                </div>
                <div className="grid grid-cols-2 gap-y-2 gap-x-4 mb-4">
                  {[["NM",card.market,"#4ade80"],["LP",Math.round(card.market*.76),"#60a5fa"],["MP",Math.round(card.market*.6),"#f59e0b"],["HP",Math.round(card.market*.4),"#ef4444"]].map(([c,p,col])=>(
                    <div key={c} className="flex items-center gap-2"><div className="w-1 h-4 rounded-full flex-shrink-0" style={{background:col}}/><span className="text-xs text-gray-500">{c}</span><span className="text-white text-sm font-medium">${p.toLocaleString()}</span></div>
                  ))}
                </div>
                <div className="space-y-2">
                  {[["ODDS","1 in 1,441.44"],["COST TO PULL","$13.7k"],["SOLD","4.1/day · 29/wk"]].map(([l,v])=>(
                    <div key={l} className="flex items-center gap-2"><span className="text-gray-500 text-xs">{l}</span><Info size={11} className="text-gray-700"/><span className="text-white text-xs">{v}</span></div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold text-white mb-1">{card.name}</h1>
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <span className="text-sm font-medium cursor-pointer hover:underline" style={{color:"#a78bfa"}}>{card.set}</span>
                <span className="text-gray-600">·</span><span className="text-gray-400 text-sm">#{card.num}</span>
                <span className="text-gray-600">·</span><span className="text-gray-400 text-sm">Pokemon</span>
              </div>
              <div className="grid grid-cols-3 gap-2 mb-4">
                {[{label:"MARKET",val:`$${card.market.toLocaleString()}`,sub:"$1,036 — $1,562",badge:null},{label:"PSA 10",val:`$${card.psa10.toLocaleString()}`,sub:null,badge:"+223%"},{label:"PSA 9",val:"$1,288",sub:null,badge:"+-8%"}].map(b=>(
                  <div key={b.label} className="rounded-xl border border-gray-800 p-3" style={{background:"#0f0f0f"}}>
                    <div className="flex items-center gap-1 mb-1"><span className="text-xs text-gray-500 uppercase tracking-wide">{b.label}</span><Info size={10} className="text-gray-700"/></div>
                    <div className="text-white text-xl font-bold">{b.val}</div>
                    {b.sub&&<div className="text-gray-600 text-xs mt-0.5">{b.sub}</div>}
                    {b.badge&&<div className="text-green-400 text-xs mt-0.5">{b.badge}</div>}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                <div className="flex items-baseline gap-2">
                  <span className="text-white text-xl font-bold">${cur.toLocaleString()}</span>
                  <span className={`text-sm font-medium ${chg>=0?"text-green-400":"text-red-400"}`}>+${Math.abs(chg)} ({chgP}%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-lg border border-gray-700 overflow-hidden">
                    {["Raw","PSA 10"].map(m=>(
                      <button key={m} onClick={()=>setMode(m)} className={`px-3 py-1 text-xs font-medium transition-colors ${mode===m?"bg-gray-700 text-white":"text-gray-400 hover:text-white"}`}>{m}</button>
                    ))}
                  </div>
                  <button className="p-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white transition-colors"><TrendingUp size={14}/></button>
                  <button className="p-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white transition-colors"><BarChart2 size={14}/></button>
                </div>
              </div>
              <div className="rounded-xl border border-gray-800 p-3 mb-2" style={{background:"#0a0a0a"}}>
                <LineChart data={data} dates={CHART_DATES}/>
              </div>
              <div className="flex gap-1 mb-1">
                {["1M","3M","6M","1Y","ALL"].map(p=>(
                  <button key={p} onClick={()=>setPeriod(p)} className="text-xs px-3 py-1 rounded-md transition-all duration-150"
                    style={period===p?{background:"#fff",color:"#000",fontWeight:700}:{color:"#6b7280"}}>{p}</button>
                ))}
              </div>
              <div className="text-xs text-gray-700 mb-4">Last updated: Mar 26, 2026 2:14 AM</div>
              <div className="flex gap-2 mb-6 flex-wrap">
                <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-700 text-white text-sm font-medium hover:bg-gray-900 transition-colors"><Heart size={14} className="text-gray-400"/> Save</button>
                <button className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-sm font-medium" style={{background:"linear-gradient(135deg,#6366f1,#ec4899)"}}><Plus size={14}/> Add to Collection</button>
                <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-700 text-white text-sm font-medium hover:bg-gray-900 transition-colors"><Bell size={14} className="text-gray-400"/> Alert</button>
              </div>
              <MarketSentiment card={card}/>
              <div className="rounded-xl border border-yellow-900/40 p-4 mb-3 flex items-center justify-between" style={{background:"#0e0c00"}}>
                <div className="flex items-center gap-2"><Lock size={16} className="text-yellow-600"/>
                  <div><div className="text-white text-sm font-medium">Gradeability Indicators</div><div className="text-gray-500 text-xs mt-0.5">Unlock with Prime for full access</div></div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="text-xs font-bold px-3 py-1.5 rounded-lg" style={{background:"#78350f",color:"#fbbf24"}}>PRIME</button>
                  <ChevronRight size={16} className="text-gray-600"/>
                </div>
              </div>
              <div className="flex border-b border-gray-800 mb-4 mt-6">
                {["Grading","Listings","Related"].map(t=>(
                  <button key={t} onClick={()=>setActiveTab(t)} className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 ${activeTab===t?"text-white border-white":"text-gray-500 border-transparent hover:text-gray-300"}`}>{t}</button>
                ))}
              </div>
              {activeTab==="Grading"&&<><GradingBreakdown/><PopulationReport/><PullCalculator/></>}
              {activeTab==="Listings"&&<div className="rounded-xl border border-gray-800 p-8 text-center" style={{background:"#0f0f0f"}}><div className="text-gray-500 text-sm">Active marketplace listings coming soon</div></div>}
              {activeTab==="Related"&&<div className="grid grid-cols-2 gap-3">{CARDS.slice(0,4).map(c=>(
                <div key={c.id} className="rounded-xl border border-gray-800 p-3 flex gap-3 hover:bg-gray-900 cursor-pointer transition-colors" style={{background:"#0f0f0f"}}>
                  <img src={c.img} alt={c.name} className="w-12 h-16 object-cover rounded-lg flex-shrink-0" onError={e=>{e.target.src=`https://placehold.co/48x64/0a0a1a/6366f1?text=?`}}/>
                  <div className="min-w-0"><div className="text-white text-xs font-medium truncate">{c.name}</div><div className="text-gray-500 text-xs truncate">{c.set}</div><div className="text-white text-sm font-bold mt-1">${c.market.toLocaleString()}</div></div>
                </div>
              ))}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Product Detail View ──────────────────────────────────────────────────────

function ProductDetailView({product,onBack}){
  const [period,setPeriod]=useState("1M");
  const [activeTab,setActiveTab]=useState("Cards inside");
  const prodDates=generateDates(PROD_DATA.length);
  const cur=PROD_DATA[PROD_DATA.length-1],chg=(cur-PROD_DATA[0]),chgP=((chg/PROD_DATA[0])*100).toFixed(1);
  return(
    <div className="min-h-screen flex flex-col" style={{background:"#000"}}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-900 sticky top-0 z-30" style={{background:"#080808"}}>
        <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors"><ChevronLeft size={20}/></button>
        <div className="flex items-center gap-2">
          <img src={product.img} alt={product.name} className="w-6 h-8 object-cover rounded" onError={e=>{e.target.src="https://placehold.co/28x40/0a1a0a/22c55e?text=?"}}/>
          <div><div className="text-white text-sm font-medium">{product.name}</div><div className="text-xs" style={{color:"#a78bfa"}}>{product.set}</div></div>
        </div>
        <button className="text-gray-400 hover:text-white transition-colors"><Share2 size={18}/></button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left */}
            <div className="lg:w-72 flex-shrink-0">
              <div className="lg:sticky lg:top-4 space-y-3">
                <div className="rounded-2xl overflow-hidden border border-gray-800 relative" style={{background:"#111"}}>
                  <img src={product.img} alt={`${product.name} sealed product box`} className="w-full object-contain" style={{maxHeight:280}} onError={e=>{e.target.src=`https://placehold.co/400x400/0a1a0a/22c55e?text=${encodeURIComponent(product.name)}`}}/>
                  <div className="absolute bottom-2 left-2 text-xs font-bold px-2 py-0.5 rounded" style={{background:"rgba(0,0,0,0.8)",color:"#9ca3af",border:"1px solid #374151"}}>BOOSTER BUNDLE</div>
                </div>
                {/* Rip vs Flip compact */}
                <RipVsFlip compact/>
              </div>
            </div>
            {/* Right */}
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold text-white mb-1">{product.name}</h1>
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <span className="text-sm font-medium cursor-pointer hover:underline" style={{color:"#a78bfa"}}>{product.set}</span>
                <span className="text-gray-600">·</span><span className="text-gray-400 text-sm">Pokemon</span>
                <span className="text-gray-600">·</span><span className="text-gray-400 text-sm">MEGA</span>
              </div>
              {/* Price header */}
              <div className="flex items-baseline gap-2 mb-3">
                <span className="text-white text-xl font-bold">${product.market.toFixed(2)}</span>
                <span className={`text-sm font-medium ${chg>=0?"text-green-400":"text-red-400"}`}>+${Math.abs(chg).toFixed(2)} (+{chgP}%)</span>
              </div>
              {/* Timeframe dots */}
              <div className="flex gap-2 mb-2">
                {["7","14","21","50","100","200"].map(t=>(
                  <button key={t} className="flex items-center gap-1 text-xs text-gray-500 hover:text-white transition-colors px-2 py-0.5 rounded">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-600"/>
                    {t}
                  </button>
                ))}
              </div>
              {/* Chart */}
              <div className="rounded-xl border border-gray-800 p-3 mb-2" style={{background:"#0a0a0a"}}>
                <LineChart data={PROD_DATA} dates={prodDates} color="#4ade80"/>
              </div>
              <div className="flex gap-1 mb-1">
                {["1M","3M","6M","1Y","ALL"].map(p=>(
                  <button key={p} onClick={()=>setPeriod(p)} className="text-xs px-3 py-1 rounded-md transition-all duration-150"
                    style={period===p?{background:"#fff",color:"#000",fontWeight:700}:{color:"#6b7280"}}>{p}</button>
                ))}
              </div>
              {/* Market / Expected Value boxes */}
              <div className="grid grid-cols-2 gap-3 mt-4 mb-4">
                <div className="rounded-xl border border-gray-800 p-4" style={{background:"#0f0f0f"}}>
                  <div className="flex items-center gap-1 mb-2"><span className="text-xs text-gray-500 uppercase tracking-wider">MARKET PRICE</span><Info size={10} className="text-gray-700"/></div>
                  <div className="text-white text-3xl font-bold">${product.market.toFixed(2)}</div>
                </div>
                <div className="rounded-xl border border-cyan-900/40 p-4" style={{background:"#011a1a"}}>
                  <div className="flex items-center gap-1 mb-2"><span className="text-xs uppercase tracking-wider" style={{color:"#22d3ee"}}>EXPECTED VALUE</span><Info size={10} className="text-gray-700"/></div>
                  <div className="text-white text-3xl font-bold">$22.87</div>
                  <div className="text-gray-500 text-xs mt-1">Avg value of cards inside</div>
                </div>
              </div>
              {/* Actions */}
              <div className="flex gap-2 mb-6 flex-wrap">
                <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-gray-700 text-white text-sm font-medium hover:bg-gray-900 transition-colors"><Bookmark size={14} className="text-gray-400"/> Save</button>
                <button className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-white text-sm font-medium" style={{background:"linear-gradient(135deg,#6366f1,#ec4899)"}}><Plus size={14}/> Add to Collection</button>
              </div>
              {/* Buy Signal locked */}
              <div className="rounded-xl border border-gray-800 p-6 mb-4 text-center" style={{background:"#0f0f0f"}}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3" style={{background:"#1a1200"}}>
                  <Lock size={18} className="text-yellow-500"/>
                </div>
                <div className="text-white text-sm font-semibold mb-1">Buy Signal Analysis</div>
                <div className="text-gray-500 text-xs mb-3">Unlock with Prime</div>
                <button className="px-4 py-2 rounded-lg text-sm font-bold" style={{background:"#78350f",color:"#fbbf24"}}>Get Prime</button>
              </div>
              {/* Cards Inside / Related tabs */}
              <div className="flex rounded-xl border border-gray-800 overflow-hidden mb-4" style={{background:"#0a0a0a"}}>
                {["Cards inside","Related Products"].map(t=>(
                  <button key={t} onClick={()=>setActiveTab(t)}
                    className={`flex-1 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${activeTab===t?"text-white bg-gray-800":"text-gray-500 hover:text-gray-300"}`}>
                    {t==="Cards inside"?<Package size={14}/>:<Layers size={14}/>}{t}
                  </button>
                ))}
              </div>
              {activeTab==="Cards inside"&&(
                <>
                  <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{background:"#1e1b4b"}}><Package size={16} className="text-indigo-400"/></div>
                      <div><div className="text-white text-sm font-semibold">Cards You Can Open</div><div className="text-gray-500 text-xs">Potential pulls from this product</div></div>
                      <Info size={12} className="text-gray-700"/>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-green-700 text-green-400 hover:bg-green-950 transition-colors"><Plus size={11}/> Add Set</button>
                      <button className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800 transition-colors"><Eye size={11}/> Show Missing</button>
                      <span className="text-xs font-bold px-2 py-1 rounded-lg" style={{background:"#1e1b4b",color:"#818cf8"}}>215 / 215</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 text-xs hover:bg-gray-800 transition-colors"><Filter size={12}/> Filters <span className="text-white font-bold">1</span></button>
                    <div className="ml-auto flex items-center gap-2">
                      <span className="text-xs text-gray-500">Sort:</span>
                      <button className="flex items-center gap-1 text-xs text-white border border-gray-700 px-2 py-1 rounded-lg">Market <ChevronDown size={11}/></button>
                      <button className="p-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white transition-colors"><ArrowDown size={12}/></button>
                    </div>
                  </div>
                  <div className="grid gap-3" style={{gridTemplateColumns:"repeat(auto-fill, minmax(175px, 1fr))"}}>
                    {PRODUCT_CARDS_INSIDE.map(card=>(
                      <MiniCardCell key={card.id} card={card}/>
                    ))}
                  </div>
                </>
              )}
              {activeTab==="Related Products"&&(
                <div className="grid grid-cols-2 gap-4">
                  {PRODUCTS.slice(0,4).map(p=>(
                    <div key={p.id} className="rounded-xl border border-gray-800 overflow-hidden hover:border-gray-600 cursor-pointer transition-colors" style={{background:"#0f0f0f"}}>
                      <img src={p.img} alt={p.name} className="w-full h-32 object-cover" onError={e=>{e.target.src=`https://placehold.co/400x300/0a1a1a/34d399?text=${encodeURIComponent(p.name)}`}}/>
                      <div className="p-3"><div className="text-white text-xs font-medium truncate">{p.name}</div><div className="text-gray-500 text-xs">{p.set}</div><div className="text-white font-bold text-sm mt-1">${p.market}</div></div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniCardCell({card}){
  return(
    <div className="rounded-xl border border-gray-800 overflow-hidden cursor-pointer hover:border-gray-600 hover:scale-[1.02] transition-all duration-200" style={{background:"#111"}}>
      <div className="relative overflow-hidden" style={{background:"#0d0d0d"}}>
        <img src={card.img} alt={`${card.name} card art`} className="w-full h-44 object-cover transition-transform duration-300 hover:scale-105" onError={e=>{e.target.src=`https://placehold.co/220x310/1a0a0a/ef4444?text=${encodeURIComponent(card.name)}`}}/>
        <div className={`absolute top-1.5 left-1.5 text-xs font-bold px-1.5 py-0.5 rounded backdrop-blur-sm ${card.change>=0?"text-green-400 bg-green-950/80":"text-red-400 bg-red-950/80"}`}>
          {card.change>=0?"+":""}${card.change.toFixed(2)}
        </div>
      </div>
      <div className="p-2">
        <div className="flex items-start justify-between gap-1 mb-1.5">
          <div className="min-w-0">
            <div className="text-white text-xs font-medium truncate leading-tight">{card.name}</div>
            <div className="text-gray-500 text-xs truncate mt-0.5 leading-tight">{card.set} · {card.num}</div>
          </div>
          <button className="text-gray-600 hover:text-white transition-colors flex-shrink-0"><Plus size={12}/></button>
        </div>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-gray-600 uppercase tracking-wide" style={{fontSize:"9px"}}>MARKET</div>
            <div className="text-white font-bold text-xs">${card.market.toLocaleString()}</div>
          </div>
          <div className="text-right">
            <div className="flex items-center justify-end gap-0.5">
              <span className="text-gray-500" style={{fontSize:"9px"}}>PSA 10</span>
              <span className="font-bold px-1 rounded-full" style={{background:"rgba(74,222,128,0.15)",color:"#4ade80",fontSize:"9px",lineHeight:"16px"}}>+{card.psa10pct}%</span>
            </div>
            <div className="text-white font-bold text-xs">${card.psa10.toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Collection View ──────────────────────────────────────────────────────────

function CollectionView(){
  const [tab,setTab]=useState("Collection");
  return(
    <div className="flex-1 px-4 md:px-8 py-8">
      <div className="flex items-start justify-between mb-2 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Collection Portfolio</h1>
          <p className="text-gray-500 text-sm mt-1">Track your cards, monitor performance, and find grading opportunities</p>
        </div>
        <div className="flex rounded-xl border border-gray-700 overflow-hidden" style={{background:"#0a0a0a"}}>
          {["Collection","Binders"].map(t=>(
            <button key={t} onClick={()=>setTab(t)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-all ${tab===t?"text-white bg-gray-800":"text-gray-500 hover:text-gray-300"}`}>
              {t==="Collection"?<LayoutGrid size={14}/>:<BookOpen size={14}/>}{t}
            </button>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-gray-800 flex items-center justify-center" style={{background:"#0a0a0a",minHeight:380}}>
        <div className="text-center px-6 py-12 max-w-sm">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{background:"#0d1f3c",border:"1px solid #1e3a5f"}}>
            <ShieldCheck size={28} style={{color:"#38bdf8"}}/>
          </div>
          <h2 className="text-white text-xl font-bold mb-3">Start Your Collection</h2>
          <p className="text-gray-400 text-sm leading-relaxed mb-6">Track your cards and sealed products. See real-time valuations, portfolio analytics, and discover which cards to grade.</p>
          <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-white text-sm font-semibold mx-auto transition-all hover:opacity-90"
            style={{background:"linear-gradient(135deg,#06b6d4,#0284c7)"}}>
            <Search size={14}/> Browse Cards
          </button>
          <div className="flex items-center justify-center gap-3 mt-6 flex-wrap">
            {[{icon:TrendIcon,label:"Track Value"},{icon:TrendingUp,label:"See Trends"},{icon:Award,label:"Grade Tips"}].map(({icon:Icon,label})=>(
              <div key={label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-800 text-gray-400 text-xs" style={{background:"#111"}}>
                <Icon size={12}/>{label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Card Grid ────────────────────────────────────────────────────────────────

function CardGrid({cards,onCardClick}){
  return(
    <div className="grid gap-3" style={{gridTemplateColumns:"repeat(auto-fill, minmax(175px, 1fr))"}}>
      {cards.map(card=>(
        <TiltCard key={card.id} className="rounded-xl border border-gray-800 overflow-hidden cursor-pointer group" style={{background:"#111"}}>
          <div onClick={()=>onCardClick(card)} className="h-full" style={{background:"#111",borderRadius:"0.75rem"}}>
            <div className="relative overflow-hidden" style={{background:"#0d0d0d"}}>
              <img src={card.img} alt={`${card.name} trading card holographic artwork`} className="w-full h-44 object-cover transition-transform duration-300 group-hover:scale-105" onError={e=>{e.target.src=`https://placehold.co/220x310/0a0a1a/6366f1?text=${encodeURIComponent(card.name)}`}}/>
              <div className={`absolute top-1.5 left-1.5 text-xs font-bold px-1.5 py-0.5 rounded backdrop-blur-sm ${card.change>=0?"text-green-400 bg-green-950/80":"text-red-400 bg-red-950/80"}`}>
                {card.change>=0?"+":""}${card.change.toFixed(2)}
              </div>
            </div>
            <div className="p-2">
              <div className="flex items-start justify-between gap-1 mb-1.5">
                <div className="min-w-0">
                  <div className="text-white text-xs font-medium truncate leading-tight">{card.name}</div>
                  <div className="text-gray-500 text-xs truncate mt-0.5 leading-tight">{card.set} · {card.num}</div>
                </div>
                <button className="text-gray-600 hover:text-white transition-colors flex-shrink-0"><Plus size={12}/></button>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-gray-600 text-xs uppercase tracking-wide" style={{fontSize:"9px"}}>MARKET</div>
                  <div className="text-white font-bold text-xs">${card.market.toLocaleString()}</div>
                </div>
                <div className="text-right">
                  <div className="flex items-center justify-end gap-0.5">
                    <span className="text-gray-500" style={{fontSize:"9px"}}>PSA 10</span>
                    <span className="font-bold px-1 rounded-full" style={{background:"rgba(74,222,128,0.15)",color:"#4ade80",fontSize:"9px",lineHeight:"16px"}}>+{card.psa10pct}%</span>
                  </div>
                  <div className="text-white font-bold text-xs">${card.psa10.toLocaleString()}</div>
                </div>
              </div>
            </div>
          </div>
        </TiltCard>
      ))}
    </div>
  );
}

// ─── Product Grid ─────────────────────────────────────────────────────────────

const PULL_RATE_STYLE={
  Good:    {bg:"#052e16",text:"#4ade80"},
  Mid:     {bg:"#1c1400",text:"#eab308"},
  Garbage: {bg:"#2d0a0a",text:"#f87171"},
  Amazing: {bg:"#0c1a2e",text:"#22d3ee"},
};

function ProductGrid({products,onProductClick}){
  return(
    <div className="grid gap-3" style={{gridTemplateColumns:"repeat(auto-fill, minmax(175px, 1fr))"}}>
      {products.map(p=>{
        const pr=PULL_RATE_STYLE[p.pullRate]||PULL_RATE_STYLE.Mid;
        return(
          <div key={p.id} onClick={()=>onProductClick(p)}
            className="rounded-xl border border-gray-800 overflow-hidden cursor-pointer hover:border-gray-600 hover:scale-[1.02] transition-all duration-200"
            style={{background:"#111"}}>
            <div className="relative" style={{background:"#0d0d0d"}}>
              <img src={p.img} alt={`${p.name} sealed Pokemon product`} className="w-full h-44 object-contain p-2 transition-transform duration-300 hover:scale-105" onError={e=>{e.target.src=`https://placehold.co/260x340/0a1a1a/34d399?text=${encodeURIComponent(p.name)}`}}/>
              <div className={`absolute top-1.5 right-1.5 text-xs font-bold px-1.5 py-0.5 rounded backdrop-blur-sm ${p.change>=0?"text-green-400 bg-green-950/80":"text-red-400 bg-red-950/80"}`}>
                {p.change>=0?"+":""}${p.change.toFixed(2)}
              </div>
            </div>
            <div className="p-2">
              <div className="flex items-start justify-between gap-1 mb-1.5">
                <div className="min-w-0">
                  <div className="text-white text-xs font-medium truncate leading-tight">{p.name}</div>
                  <div className="text-gray-500 text-xs truncate mt-0.5">{p.set}</div>
                </div>
                <button className="text-gray-600 hover:text-white transition-colors flex-shrink-0"><Plus size={12}/></button>
              </div>
              <div className="grid grid-cols-2 gap-0 rounded-lg overflow-hidden">
                <div className="p-1.5" style={{background:"#1a1a1a"}}>
                  <div className="text-gray-600 uppercase tracking-wide mb-0.5" style={{fontSize:"9px"}}>MARKET</div>
                  <div className="text-white font-bold text-xs">${p.market.toLocaleString()}</div>
                </div>
                <div className="p-1.5" style={{background:pr.bg}}>
                  <div className="uppercase tracking-wide mb-0.5" style={{color:pr.text,opacity:0.7,fontSize:"9px"}}>PULL RATES</div>
                  <div className="font-bold text-xs" style={{color:pr.text}}>{p.pullRate}</div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

const NAV_ITEMS=[
  {id:"Discover",   label:"Discover",     Icon:Grid},
  {id:"Insights",   label:"Insights",     Icon:TrendingUp},
  {id:"PackBattles",label:"Pack Battles", Icon:Swords},
  {id:"Collection", label:"Collection",   Icon:LayoutGrid},
  {id:"Alerts",     label:"Alerts",       Icon:Bell},
];

export default function PackMagik(){
  const [page,setPage]          = useState("Discover");
  const [query,setQuery]        = useState("");
  const [showSugg,setShowSugg]  = useState(false);
  const [ddVisible,setDDVis]    = useState(false);
  const [activeNav,setActiveNav]= useState("Cards");
  const [activeCat,setActiveCat]= useState("Pokemon");
  const [selCard,setSelCard]     = useState(null);
  const [selProd,setSelProd]     = useState(null);
  const [sidebarOpen,setSidebarOpen] = useState(false);
  const timerRef=useRef(null);
  const sidebarTimer=useRef(null);
  const openSidebar  = () => { clearTimeout(sidebarTimer.current); setSidebarOpen(true); };
  const closeSidebar = () => { sidebarTimer.current = setTimeout(() => setSidebarOpen(false), 80); };

  const isProducts=activeNav==="Products";
  const suggestions = query.length>1 ? (isProducts?SEARCH_SUGGESTIONS_PRODUCTS:SEARCH_SUGGESTIONS_CARDS) : [];
  const showDrop    = showSugg && suggestions.length>0;

  useEffect(()=>{
    if(showDrop){setDDVis(true);}
    else{const t=setTimeout(()=>setDDVis(false),220);return()=>clearTimeout(t);}
  },[showDrop]);

  // Route to detail views
  if(selCard) return <CardDetailView card={selCard} onBack={()=>setSelCard(null)}/>;
  if(selProd) return <ProductDetailView product={selProd} onBack={()=>setSelProd(null)}/>;

  const navIcons={Cards:Grid,Sets:Package,Products:Package,Listings:List};
  const categories=["All","Pokemon","English","Japanese"];
  const primaryNavItems=["Cards","Sets","Products","Listings"];

  const sortLabel=isProducts?"Release":"Market";
  const placeholderText=isProducts?`Search "Rayquaza"...`:`Search "Pikachu"...`;
  const discoverTitle=isProducts?"Products":"Cards";

  return(
    <div className="flex min-h-screen" style={{background:"#000",fontFamily:"system-ui,-apple-system,sans-serif"}}>

      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <div
        className="hidden md:flex fixed left-0 top-0 h-full flex-col border-r border-gray-900"
        style={{
          background:"#080808",
          width: sidebarOpen ? "180px" : "48px",
          transition:"width 0.22s cubic-bezier(0.4,0,0.2,1)",
          zIndex: 50,
          overflowX:"hidden",
          overflowY:"hidden",
        }}
        onMouseEnter={openSidebar}
        onMouseLeave={closeSidebar}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-3 py-4 border-b border-gray-900 flex-shrink-0" style={{minHeight:56}}>
          <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{background:"linear-gradient(135deg,#a855f7,#ec4899)"}}>
            <Zap size={14} className="text-white"/>
          </div>
          <span className="text-white font-bold text-sm whitespace-nowrap overflow-hidden"
            style={{opacity:sidebarOpen?1:0, transition:"opacity 0.15s ease", maxWidth:sidebarOpen?"120px":"0px"}}>
            Pack Magik
          </span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-hidden min-h-0">
          {NAV_ITEMS.map(({id,label,Icon})=>{
            const active=page===id;
            return(
              <button key={id} onClick={()=>setPage(id)}
                className={`w-full flex items-center gap-3 rounded-lg text-sm font-medium transition-colors ${active?"text-white bg-gray-800":"text-gray-500 hover:text-gray-300 hover:bg-gray-900/60"}`}
                style={{padding:"10px", minWidth:0, justifyContent:"flex-start"}}>
                <Icon size={16} style={{flexShrink:0}}/>
                <span className="whitespace-nowrap overflow-hidden"
                  style={{opacity:sidebarOpen?1:0, transition:"opacity 0.12s ease", maxWidth:sidebarOpen?"120px":"0px"}}>
                  {label}
                </span>
              </button>
            );
          })}
          <div style={{paddingTop:"8px", marginTop:"8px", borderTop:"1px solid #1f2937"}}>
            <button
              className="w-full flex items-center gap-3 rounded-lg text-sm font-medium text-gray-500 hover:text-gray-300 hover:bg-gray-900/60 transition-colors"
              style={{padding:"10px", minWidth:0, justifyContent:"flex-start"}}>
              <ChevronDown size={16} style={{flexShrink:0}}/>
              <span className="whitespace-nowrap overflow-hidden"
                style={{opacity:sidebarOpen?1:0, transition:"opacity 0.12s ease", maxWidth:sidebarOpen?"120px":"0px"}}>
                More
              </span>
            </button>
          </div>
        </nav>

        {/* Bottom */}
        <div className="px-2 pb-5 border-t border-gray-900 pt-3 space-y-2 flex-shrink-0 overflow-hidden">
          <div className="flex items-center gap-2 rounded-lg cursor-pointer hover:bg-gray-900/60 transition-colors"
            style={{padding:"8px 10px"}}>
            <div className="w-6 h-6 rounded bg-gray-700 flex items-center justify-center text-xs text-gray-300 font-medium" style={{flexShrink:0}}>US</div>
            <span className="text-gray-400 text-xs whitespace-nowrap overflow-hidden"
              style={{opacity:sidebarOpen?1:0, transition:"opacity 0.12s ease", maxWidth:sidebarOpen?"80px":"0px"}}>
              USD
            </span>
            <ChevronDown size={12} className="text-gray-600" style={{marginLeft:"auto", flexShrink:0, opacity:sidebarOpen?1:0, transition:"opacity 0.12s ease"}}/>
          </div>
          <div className="flex items-center gap-2 rounded-lg hover:bg-gray-900/60 cursor-pointer transition-colors"
            style={{padding:"8px 10px"}}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs text-white font-bold" style={{background:"linear-gradient(135deg,#f97316,#ef4444)", flexShrink:0}}>T</div>
            <span className="text-white text-xs font-medium whitespace-nowrap overflow-hidden"
              style={{opacity:sidebarOpen?1:0, transition:"opacity 0.12s ease", maxWidth:sidebarOpen?"100px":"0px"}}>
              tonycollects
            </span>
          </div>
        </div>
      </div>

      {/* Mobile bottom nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 border-t border-gray-800 z-20 flex" style={{background:"#080808"}}>
        {NAV_ITEMS.slice(0,5).map(({id,label,Icon})=>(
          <button key={id} onClick={()=>setPage(id)}
            className={`flex-1 flex flex-col items-center py-2 gap-1 text-xs transition-colors ${page===id?"text-white":"text-gray-600"}`}>
            <Icon size={18}/><span className="text-xs">{label}</span>
          </button>
        ))}
      </div>

      {/* ── Main Content ─────────────────────────────────────────────── */}
      <div className="flex-1 mb-16 md:mb-0 flex flex-col md:ml-12" style={{minWidth: 0}}>

        {/* Collection view */}
        {page==="Collection"&&<CollectionView/>}

        {/* Discover view */}
        {page==="Discover"&&(
          <>
            {/* Backdrop */}
            {ddVisible&&(
              <div className="fixed inset-0 z-30 transition-opacity duration-200"
                style={{background:"rgba(0,0,0,0.8)",opacity:showDrop?1:0,pointerEvents:showDrop?"auto":"none"}}
                onMouseDown={()=>setShowSugg(false)}/>
            )}

            {/* Hero */}
            <div className="pt-10 pb-6 text-center px-4 md:px-8 relative z-40">
              <h1 className="text-4xl font-bold text-white mb-2">
                Discover{" "}
                <span style={{background:"linear-gradient(90deg,#f59e0b,#ec4899,#a855f7)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
                  {discoverTitle}
                </span>
              </h1>
              <p className="text-gray-500 text-sm mb-6">Search 50,000+ cards with real-time prices and market signals</p>

              {/* Search bar */}
              <div className="relative max-w-3xl mx-auto">
                <div className="flex items-center rounded-2xl border px-4 py-2.5 gap-2 transition-all"
                  style={{background:"#0f0f0f",borderColor:showDrop?"#6366f1":"#374151",boxShadow:showDrop?"0 0 0 1px #6366f1,0 0 20px rgba(99,102,241,0.12)":"none",position:"relative",zIndex:50}}>
                  <Search size={16} className="text-gray-500 flex-shrink-0"/>
                  <input type="text" value={query}
                    onChange={e=>{setQuery(e.target.value);setShowSugg(true);}}
                    onFocus={()=>setShowSugg(true)}
                    onBlur={()=>{timerRef.current=setTimeout(()=>setShowSugg(false),180);}}
                    placeholder={placeholderText}
                    className="flex-1 bg-transparent text-white text-sm outline-none placeholder-gray-600"/>
                  {query&&<button onClick={()=>{setQuery("");setShowSugg(false);}} className="text-gray-600 hover:text-gray-400 transition-colors"><X size={14}/></button>}
                  <button className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-xl text-white border border-gray-700 bg-transparent hover:bg-gray-800 transition-colors">
                    <Zap size={12} className="text-gray-400"/> Scan
                  </button>
                </div>

                {/* Dropdown */}
                {ddVisible&&(
                  <div className="absolute top-full left-0 right-0 mt-1 rounded-2xl border border-gray-700 overflow-hidden shadow-2xl"
                    style={{background:"#111",zIndex:60,opacity:showDrop?1:0,transform:showDrop?"translateY(0)":"translateY(-6px)",transition:"opacity 0.18s ease, transform 0.18s ease",pointerEvents:showDrop?"auto":"none"}}
                    onMouseDown={e=>e.preventDefault()}>
                    <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">SETS</span>
                      <button onClick={()=>setShowSugg(false)} className="text-gray-600 hover:text-gray-400"><X size={12}/></button>
                    </div>
                    {suggestions.filter(s=>s.type==="set").map((s,i)=>(
                      <div key={i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-900 cursor-pointer transition-colors">
                        <div className="w-9 h-6 rounded bg-gray-800 overflow-hidden flex-shrink-0"><img src="https://images.pokemontcg.io/sv8pt5/logo.png" alt="Set thumbnail" className="w-full h-full object-contain p-0.5" style={{background:"#1a1a2e"}}/></div>
                        <div className="flex-1 min-w-0"><div className="text-white text-sm truncate">{s.name}</div><div className="text-gray-500 text-xs">{s.sub}</div></div>
                        {s.price&&<span className="text-white text-sm font-medium">{s.price}</span>}
                        <span className="text-xs font-medium px-2 py-0.5 rounded" style={{background:"#1f1f1f",color:"#9ca3af"}}>SET</span>
                      </div>
                    ))}
                    <div className="px-4 py-2 border-t border-gray-800"><span className="text-xs font-medium text-gray-500 uppercase tracking-wider">CARDS</span></div>
                    {suggestions.filter(s=>s.type==="card").map((s,i)=>(
                      <div key={i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-900 cursor-pointer transition-colors">
                        <div className="w-7 h-9 rounded bg-gray-800 overflow-hidden flex-shrink-0"><img src="https://images.pokemontcg.io/sv8pt5/33_hires.png" alt={`${s.name} thumbnail`} className="w-full h-full object-cover"/></div>
                        <div className="flex-1 min-w-0"><div className="text-white text-sm truncate">{s.name}</div><div className="text-gray-500 text-xs truncate">{s.sub}</div></div>
                        <span className="text-white text-sm font-medium">{s.price}</span>
                        <span className="text-xs font-medium px-2 py-0.5 rounded" style={{background:"#1f1f1f",color:"#9ca3af"}}>CARD</span>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 px-4 py-2.5 border-t border-gray-800 text-gray-600 hover:bg-gray-900 cursor-pointer transition-colors">
                      <Search size={12}/><span className="text-sm">Search {isProducts?"Products":"Cards"}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Nav bar */}
            <div className="flex flex-col items-center gap-3 px-4 md:px-8 mb-6">
              <div className="flex items-center gap-1 p-1 rounded-xl border border-gray-800" style={{background:"#0a0a0a"}}>
                {primaryNavItems.map(item=>{
                  const Icon=navIcons[item];
                  return(
                    <button key={item} onClick={()=>setActiveNav(item)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${activeNav===item?"text-white bg-gray-800 border border-gray-600":"text-gray-500 hover:text-gray-300"}`}>
                      <Icon size={13}/>{item}
                    </button>
                  );
                })}
              </div>
              <div className="flex items-center gap-2 flex-wrap justify-center">
                {categories.map(cat=>(
                  <button key={cat} onClick={()=>setActiveCat(cat)}
                    className="px-3 py-1.5 rounded-full text-sm font-medium transition-all border"
                    style={activeCat===cat?{color:"#fff",borderColor:"#fff",background:"#1f1f1f"}:{color:"#6b7280",borderColor:"#374151",background:"transparent"}}>
                    {cat}
                  </button>
                ))}
                <div className="w-px h-5 bg-gray-800"/>
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-gray-400 border border-gray-700 hover:border-gray-500 hover:text-white transition-all">
                  <Filter size={13}/> Filters
                  <span className="w-4 h-4 rounded-full bg-gray-600 text-white text-xs flex items-center justify-center">1</span>
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-gray-400 border border-gray-700 hover:border-gray-500 hover:text-white transition-all">
                  Sort: {sortLabel} <ChevronDown size={12}/>
                </button>
                <button className="p-2 rounded-full text-gray-400 border border-gray-700 hover:border-gray-500 hover:text-white transition-all">
                  <ArrowDown size={14}/>
                </button>
              </div>
            </div>

            {/* Grid */}
            <div className="pb-12 px-4 md:px-8">
              {isProducts
                ? <ProductGrid products={PRODUCTS} onProductClick={setSelProd}/>
                : <CardGrid cards={CARDS} onCardClick={setSelCard}/>
              }
            </div>
          </>
        )}

        {/* Stub pages */}
        {(page==="Insights"||page==="PackBattles"||page==="Alerts")&&(
          <div className="flex-1 flex items-center justify-center px-4 py-20">
            <div className="text-center">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{background:"#111",border:"1px solid #374151"}}>
                {page==="Insights"&&<TrendingUp size={22} className="text-gray-400"/>}
                {page==="PackBattles"&&<Swords size={22} className="text-gray-400"/>}
                {page==="Alerts"&&<Bell size={22} className="text-gray-400"/>}
              </div>
              <div className="text-white text-lg font-bold mb-1">{page}</div>
              <div className="text-gray-500 text-sm">This section is coming soon.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
