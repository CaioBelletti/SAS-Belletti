import {useEffect,useState} from 'react';
import {motion,MotionConfig} from 'framer-motion';
import {ShieldCheck,Copy} from 'lucide-react';
export function Setup({root}:{root:HTMLElement}){
 const active=root.dataset.active==='true';
 const codes=Array.from(document.querySelectorAll('#auth-fallback [data-recovery-code]')).map(el=>el.textContent||'');
 const messages=Array.from(document.querySelectorAll('#auth-fallback .msg')).map(el=>el.textContent||'');
 const [notice,setNotice]=useState('');
 const [action,setAction]=useState(active?'gerar_codigos':'confirmar');
 useEffect(()=>{const fallback=document.getElementById('auth-fallback');fallback?.setAttribute('hidden','');return()=>fallback?.removeAttribute('hidden')},[]);
 return <MotionConfig reducedMotion="user"><div className="auth-setup"><motion.section className="auth-panel" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}}>
 <div className="eyebrow"><ShieldCheck size={16}/> SEGURANÇA DA CONTA</div><h1>Autenticação em duas etapas</h1>
 <p>{active?'Proteção ativa. Confirme sua identidade para alterar a configuração.':'Escaneie o QR Code com seu aplicativo autenticador e confirme o código.'}</p>
 {messages.map((m,i)=><div key={i} className="notice" role="status">{m}</div>)}
 {codes.length>0&&<section className="recovery-list"><h2>Códigos de recuperação</h2><p>Guarde agora em um local seguro. Cada código funciona uma única vez.</p>{codes.map((c,i)=><code key={i}>{c}</code>)}<button type="button" className="primary" onClick={async()=>{try{await navigator.clipboard.writeText(codes.join('\n'));setNotice('Códigos copiados. Guarde-os com segurança.')}catch{setNotice('Não foi possível copiar. Selecione os códigos manualmente.')}}}><Copy size={16}/> Copiar códigos</button><p role="status">{notice}</p></section>}
 {!active&&root.dataset.qr&&<img className="setup-qr" src={root.dataset.qr} alt="QR Code para configurar o autenticador"/>}
 <form method="post" onSubmit={e=>{if(active&&!window.confirm(action==='desativar'?'Desativar a proteção em duas etapas?':'Invalidar todos os códigos anteriores e gerar novos?'))e.preventDefault()}}>
 <input type="hidden" name="csrfmiddlewaretoken" value={root.dataset.csrf||''}/>
 <input type="hidden" name="acao" value={action}/>
 {active&&<><label htmlFor="action">Ação</label><select id="action" value={action} onChange={e=>setAction(e.target.value)}><option value="gerar_codigos">Gerar novos códigos</option><option value="desativar">Desativar 2FA</option></select></>}
 <label htmlFor="setup-password">Senha atual</label><input id="setup-password" type="password" name="password" autoComplete="current-password" required/>
 <label htmlFor="setup-code">{active?'Código autenticador ou recuperação':'Código de seis dígitos'}</label><input id="setup-code" name="codigo" autoComplete="off" inputMode={active?'text':'numeric'} maxLength={active?35:6} pattern={active?undefined:'[0-9]{6}'} required/>
 <button className="primary" type="submit">{action==='desativar'?'Desativar proteção':active?'Gerar novos códigos':'Confirmar e ativar'}</button>
 </form></motion.section></div></MotionConfig>
}
