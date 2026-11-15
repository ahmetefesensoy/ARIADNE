'use strict';
const {app,BrowserWindow,ipcMain,shell}=require('electron');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL,fileURLToPath}=require('node:url');
const crypto=require('node:crypto');
app.commandLine.appendSwitch('force-device-scale-factor','1');
let win, capture=null, timer=null, busy=false, frameIndex=0, stopping=false;
const recording=process.argv.includes('--record-tour');
const site=path.join(__dirname,'site');
const simulation=pathToFileURL(path.join(site,'simulasyon.html')).href;
const launchAt=Date.now();
function sameFile(url,file){try{return fileURLToPath(url.split('#')[0])===file;}catch{return false;}}
function allowedLocal(url){try{const p=fileURLToPath(url.split('#')[0]);return p===site||p.startsWith(site+path.sep);}catch{return false;}}
function manifest(complete=false){if(!capture)return;fs.writeFileSync(path.join(capture.folder,'manifest.json'),JSON.stringify({schema:'ariadne.viewport.recording.v1',started_at_utc:capture.started,complete,recording:!complete,source:'Ariadne application webContents.capturePage only; no desktop/microphone',width:capture.width||0,height:capture.height||0,requested_fps:12,duration_wall_s:(Date.now()-capture.clock)/1000,saved_frames:capture.frames.length,frames:capture.frames,events:capture.events,stop_reason:capture.stopReason||null,audio_recorded:false},null,2));}
async function frame(){
 if(!capture||busy||stopping||!win||win.isDestroyed())return;
 busy=true;
 try{const img=await win.webContents.capturePage();const png=img.toPNG();const size=img.getSize();
 if(!capture.width){if(size.width<640||size.height<360)throw new Error('Viewport too small');capture.width=size.width;capture.height=size.height;}
 if(size.width!==capture.width||size.height!==capture.height)throw new Error('Viewport resized; recording stopped');
 const name=`frames/frame_${String(frameIndex++).padStart(6,'0')}.png`;fs.writeFileSync(path.join(capture.folder,name),png);capture.frames.push({file:name,captured_wall_s:(Date.now()-capture.clock)/1000,sha256:crypto.createHash('sha256').update(png).digest('hex')});
 if(capture.frames.length%12===0)manifest();if((Date.now()-capture.clock)>90000)stopRecording('90-second bounded recording limit');
 }catch(e){capture.events.push({kind:'capture_error',message:String(e)});stopRecording('capture error');}finally{busy=false;}
}
function startRecording(){
 const base=process.env.ARIADNE_CAPTURE_ROOT||path.join(app.getPath('videos'),'Ariadne');
 const folder=path.join(base,'site-tour-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(path.join(folder,'frames'),{recursive:true});
 capture={folder,started:new Date().toISOString(),clock:Date.now(),frames:[],events:[]};manifest();timer=setInterval(frame,1000/12);frame();
}
function stopRecording(reason){if(!capture||stopping)return;stopping=true;clearInterval(timer);capture.stopReason=reason;manifest(true);console.log('CAPTURE_COMPLETE '+capture.folder);}
function interceptNavigation(event,url){
 if(recording&&sameFile(url,path.join(site,'simulasyon.html'))){event.preventDefault();if(capture)capture.events.push({kind:'application_link_clicked',elapsed_wall_s:(Date.now()-capture.clock)/1000,target:'simulasyon.html'});setTimeout(()=>stopRecording('Application link clicked; destination intentionally excluded'),180);return;}
 if(allowedLocal(url))return;
 event.preventDefault();if(/^https:\/\//i.test(url))shell.openExternal(url);
}
app.whenReady().then(async()=>{
 app.setName('Ariadne');
 win=new BrowserWindow({title:'Ariadne',useContentSize:true,width:1280,height:720,minWidth:960,minHeight:540,resizable:!recording,backgroundColor:'#17100c',show:false,icon:path.join(__dirname,'assets/ariadne.ico'),autoHideMenuBar:true,webPreferences:{contextIsolation:true,nodeIntegration:false,sandbox:true,preload:path.join(__dirname,'preload.cjs')}});
 win.removeMenu();win.webContents.setWindowOpenHandler(({url})=>{if(/^https:\/\//i.test(url))shell.openExternal(url);return {action:'deny'};});
 win.webContents.on('will-navigate',interceptNavigation);win.webContents.on('will-redirect',interceptNavigation);
 win.webContents.session.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
 win.webContents.on('did-finish-load',()=>{if(recording&&!capture)setTimeout(startRecording,150);});
 win.on('closed',()=>{stopRecording('Window closed');win=null;});
 await win.loadFile(path.join(__dirname,'splash.html'));win.show();
 setTimeout(()=>{if(win&&!win.isDestroyed())win.loadFile(path.join(site,'index.html'));},3200);
});
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',()=>stopRecording('Application quit'));
ipcMain.on('landing-ready',event=>{if(win&&event.sender===win.webContents)console.log('ARIADNE_READY '+(Date.now()-launchAt));});
