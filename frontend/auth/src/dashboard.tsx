import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MotionConfig,motion} from 'framer-motion';
import './dashboard.css';

const original=document.querySelector<HTMLElement>('.dashboard-sections');
if(original){
 const buttons=Array.from(original.querySelectorAll<HTMLButtonElement>('button[data-section]'));
 const host=document.createElement('div');
 original.before(host);
 function Navigation(){
  const [active,setActive]=useState(buttons.find(b=>b.getAttribute('aria-pressed')==='true')?.dataset.section||'geral');
  return <MotionConfig reducedMotion="user"><nav className="bcu-motion-nav" aria-label="Visões do dashboard">{buttons.map(b=>{
   const id=b.dataset.section!;
   return <motion.button key={id} type="button" aria-pressed={active===id} onClick={()=>{b.click();setActive(id)}} whileTap={{scale:.96}} className="bcu-motion-tab">{active===id&&<motion.span className="bcu-motion-pill" layoutId="dashboard-pill" transition={{type:'spring',stiffness:420,damping:34}}/>}<span className="bcu-motion-label">{b.textContent}</span></motion.button>
  })}</nav></MotionConfig>
 }
 createRoot(host).render(<Navigation/>);
 original.hidden=true;
}
