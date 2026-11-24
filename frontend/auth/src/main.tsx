import {createRoot} from 'react-dom/client';
import {useState,useEffect} from 'react';
import {motion, MotionConfig} from 'framer-motion';
import {Eye,EyeOff,ShieldCheck,ArrowRight,LockKeyhole} from 'lucide-react';
import './auth.css';
import {Setup} from './Setup';

const root=document.getElementById('auth-root')!;
const preview=root.dataset.preview==='true';
function Auth(){
 const [step,setStep]=useState(root.dataset.step==='2fa'?'2fa':'login');
 const [show,setShow]=useState(false);
 const [code,setCode]=useState('');
 const [busy,setBusy]=useState(false);
 const [notice,setNotice]=useState('');
 const otp=step==='2fa';
 const [recovery,setRecovery]=useState(false);
 const [remaining,setRemaining]=useState(Number(root.dataset.lock||0));
 useEffect(()=>{const deadline=Date.now()+Number(root.dataset.lock||0)*1000;const timer=window.setInterval(()=>setRemaining(Math.max(0,Math.ceil((deadline-Date.now())/1000))),250);return ()=>window.clearInterval(timer)},[]);
 useEffect(()=>{document.getElementById('auth-fallback')?.setAttribute('hidden','');document.body.classList.add('auth-enhanced');},[]);
 const messages=Array.from(document.querySelectorAll('#auth-fallback .msg')).map(el=>el.textContent||'');
 return <MotionConfig reducedMotion="user"><main className="auth-stage">
 <div className="aurora" aria-hidden="true"><i/><i/><i/></div>
 <motion.section className="auth-panel" initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.35}}>
 <header className="brand">{root.dataset.logo&&<img src={root.dataset.logo} alt="" />}<strong>BELLETTI</strong><small>CARDS UNIVERSE</small></header>
 <div className="eyebrow"><ShieldCheck size={15}/> CENTRAL DE GESTÃO</div>
 <motion.div key={step} initial={{opacity:0,x:8}} animate={{opacity:1,x:0}}>
 <h1>{otp?'Verificação de segurança':'Bem-vindo de volta.'}</h1>
 <p>{otp?'Digite os seis dígitos do seu aplicativo autenticador.':'Acesse sua central de gestão Belletti.'}</p>
 {messages.map((message,i)=><div key={i} role="alert" className="notice">{message}</div>)}
 {remaining>0&&<div role="status" className="notice">Aguarde {Math.floor(remaining/60)}:{String(remaining%60).padStart(2,'0')}</div>}
 {notice&&<div role="status" className="notice">{notice}</div>}
 <form method="post" onSubmit={e=>{if(preview){e.preventDefault();if(!otp){setStep('2fa');setNotice('');}else setNotice(code==='123456'?'Demonstração concluída.':'Use 123456 nesta demonstração.');}else setBusy(true);}}>
 <input type="hidden" name="csrfmiddlewaretoken" value={root.dataset.csrf||''}/>
 {!otp?<><label htmlFor="username">Usuário</label><input id="username" name="username" autoComplete="username" required/><label htmlFor="password">Senha</label><div className="password"><input id="password" name="password" type={show?'text':'password'} autoComplete="current-password" required/><button type="button" aria-label={show?'Ocultar senha':'Exibir senha'} onClick={()=>setShow(!show)}>{show?<EyeOff size={19}/>:<Eye size={19}/>}</button></div><input type="hidden" name="next" value={root.dataset.next||''}/></>:<><input type="hidden" name="metodo" value={recovery?'recuperacao':'totp'}/><label htmlFor="codigo">{recovery?'Código de recuperação':'Código de autenticação'}</label>{recovery?<input id="codigo" name="codigo" autoComplete="off" maxLength={35} required/>:<div className="otp-wrap"><input id="codigo" name="codigo" className="otp-input" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value.replace(/[^0-9]/g,'').slice(0,6))} onPaste={e=>{e.preventDefault();setCode(e.clipboardData.getData('text').replace(/[^0-9]/g,'').slice(0,6))}} required/><div className="otp-cells" aria-hidden="true">{Array.from({length:6},(_,i)=><span key={i}>{code[i]||'·'}</span>)}</div></div>}<button type="button" className="back" onClick={()=>{setRecovery(!recovery);setCode('')}}>{recovery?'Usar aplicativo autenticador':'Usar código de recuperação'}</button></>}
 <button className="primary" disabled={busy||remaining>0} type="submit">{busy?'Aguarde…':otp?'Verificar identidade':'Acessar plataforma'}<ArrowRight size={18}/></button>
 </form>{preview&&otp&&<button className="back" onClick={()=>{setStep('login');setCode('');setNotice('')}}>Voltar ao login</button>}
 </motion.div><footer><LockKeyhole size={13}/>{preview?'Prévia local · não use credenciais reais':'Acesso protegido'}</footer>
 </motion.section></main></MotionConfig>
}
createRoot(root).render(root.dataset.step==='setup'?<Setup root={root}/>:<Auth/>);