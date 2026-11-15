'use strict';
// No Node or filesystem API is exposed to the site.
const {ipcRenderer}=require('electron');
window.addEventListener('DOMContentLoaded',()=>ipcRenderer.send('landing-ready'),{once:true});
