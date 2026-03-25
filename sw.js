
const CACHE = 'palmer-v1';
const CDN = 'https://framerusercontent.com/images/';
const LOCAL = '/images/';

self.addEventListener('fetch', (event) => {
  const url = event.request.url;
  
  // Intercept framerusercontent.com image requests -> local
  if (url.startsWith(CDN)) {
    const urlObj = new URL(url);
    const filename = urlObj.pathname.split('/').pop();
    const localUrl = LOCAL + filename;
    
    event.respondWith(
      fetch(localUrl).catch(() => fetch(event.request))
    );
    return;
  }
});
