const gatewayUrl = document.getElementById('gatewayUrl');
const apiKey = document.getElementById('apiKey');
const saveBtn = document.getElementById('save');
const saved = document.getElementById('saved');

chrome.storage.sync.get(['gatewayUrl', 'apiKey'], (items) => {
  gatewayUrl.value = items.gatewayUrl || 'http://localhost:8080';
  apiKey.value = items.apiKey || '';
});

saveBtn.addEventListener('click', () => {
  const url = (gatewayUrl.value || '').trim().replace(/\/$/, '') || 'http://localhost:8080';
  chrome.storage.sync.set(
    {
      gatewayUrl: url,
      apiKey: (apiKey.value || '').trim(),
    },
    () => {
      saved.hidden = false;
      setTimeout(() => {
        saved.hidden = true;
      }, 2000);
    }
  );
});
