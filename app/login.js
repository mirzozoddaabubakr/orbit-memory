import {mountUniverse} from './universe.js';
const $=s=>document.querySelector(s);
mountUniverse($('.auth-art'),[],()=>{});
let signup=false;
function show(){
 const heading=signup?'Create account':'Sign in';
 $('#authHeading').textContent=$('#authSubmit').textContent=heading;
 $('#password').autocomplete=signup?'new-password':'current-password';
 $('#password').minLength=signup?12:1;$('#password').placeholder=signup?'At least 12 characters':'';
 $('#authPrompt').textContent=signup?'Already registered?':'New to Orbit?';
 $('#authSwitch').textContent=signup?'Sign in':'Create an account';
 $('#authError').textContent='';
}
$('#authSwitch').onclick=()=>{signup=!signup;$('#password').value='';show();};
$('#accountForm').onsubmit=async e=>{
 e.preventDefault();$('#authSubmit').disabled=$('#authSwitch').disabled=true;$('#authError').textContent='';
 try{
   const res=await fetch('/api/auth/'+(signup?'signup':'signin'),{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({email:$('#email').value,password:$('#password').value})});
   const data=await res.json();if(!res.ok||data.error)throw Error(data.error||'Please try again.');
   localStorage.setItem('orbit-account-change',crypto.randomUUID());
   location.replace('/');
 }catch(err){$('#authError').textContent=err.message;}
 finally{$('#authSubmit').disabled=$('#authSwitch').disabled=false;}
};
