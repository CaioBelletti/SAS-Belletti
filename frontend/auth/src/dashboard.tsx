import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MotionConfig,motion} from 'framer-motion';
import './dashboard.css';

function revealDashboard(){
 if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const cards=Array.from(document.querySelectorAll<HTMLElement>('#dashboardMetrics .metric,#widgetsContainer .dash-widget')).filter(el=>el.getClientRects().length>0);
 cards.forEach((el,i)=>{
  el.getAnimations().forEach(a=>a.cancel());
  el.animate([{opacity:0,transform:'translateY(16px) scale(.985)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:420,delay:Math.min(i*55,330),easing:'cubic-bezier(.22,1,.36,1)',fill:'backwards'});
 });
}
document.getElementById('btnPersonalizar')?.addEventListener('click',()=>requestAnimationFrame(()=>{
 const panel=document.getElementById('avisoPersonalizar');
 if(panel&&panel.getClientRects().length&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches)panel.animate([{opacity:0,transform:'translateY(-8px)'},{opacity:1,transform:'translateY(0)'}],{duration:300,easing:'ease-out'});
}));
const original=document.querySelector<HTMLElement>('.dashboard-sections');
if(original){
 const buttons=Array.from(original.querySelectorAll<HTMLButtonElement>('button[data-section]'));
 const host=document.createElement('div');
 original.before(host);
 function Navigation(){
  const [active,setActive]=useState(buttons.find(b=>b.getAttribute('aria-pressed')==='true')?.dataset.section||'geral');
  return <MotionConfig reducedMotion="user"><nav className="bcu-motion-nav" aria-label="Visões do dashboard">{buttons.map(b=>{
   const id=b.dataset.section!;
   return <motion.button key={id} type="button" aria-pressed={active===id} onClick={()=>{b.click();setActive(id);requestAnimationFrame(revealDashboard)}} whileTap={{scale:.96}} className="bcu-motion-tab">{active===id&&<motion.span className="bcu-motion-pill" layoutId="dashboard-pill" transition={{type:'spring',stiffness:420,damping:34}}/>}<span className="bcu-motion-label">{b.textContent}</span></motion.button>
  })}</nav></MotionConfig>
 }
 createRoot(host).render(<Navigation/>);
 original.hidden=true;
 requestAnimationFrame(revealDashboard);
}
