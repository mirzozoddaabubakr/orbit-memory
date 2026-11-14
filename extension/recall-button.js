if (!globalThis.orbitRecallObserver) {
  globalThis.orbitComposer.place();
  globalThis.orbitRecallObserver=new MutationObserver(()=>globalThis.orbitComposer.place());
  globalThis.orbitRecallObserver.observe(document.documentElement,{childList:true,subtree:true});
}
