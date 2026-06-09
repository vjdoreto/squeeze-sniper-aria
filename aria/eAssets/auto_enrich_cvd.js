/**
 * AUTO-ENRIQUECIMENTO CVD - Integração transparente no dashboard
 * 
 * Coloque este script ANTES do fechamento da tag </body> no doreto-squeeze-sniper.html
 * Não precisa fazer mais nada — CVD aparecerá automaticamente quando carregar o JSON
 */

class AutoEnricher {
  constructor() {
    this.serverUrl = 'http://127.0.0.1:5001/api/enrich-json';
    this.isServerReady = false;
    this.checkServer();
  }

  checkServer() {
    // Check apenas uma vez no load
    fetch('http://127.0.0.1:5001/health', { 
      method: 'GET',
      mode: 'no-cors',
      cache: 'no-cache'
    }).then(() => {
      this.isServerReady = true;
      console.log('✅ Servidor de enriquecimento CVD disponível');
    }).catch(() => {
      this.isServerReady = false;
      console.log('ℹ️  Servidor de enriquecimento não detectado (opcional)');
    });
  }

  async enrich(data) {
    if (!this.isServerReady) return data;

    try {
      const response = await fetch(this.serverUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        timeout: 5000
      });

      if (response.ok) {
        const enriched = await response.json();
        if (enriched.enriched_symbols) {
          console.log(`✅ CVD enriquecido: ${enriched.enriched_symbols} símbolos`);
        }
        return enriched;
      }
      return data;
    } catch (error) {
      console.warn('⚠️  Erro no enriquecimento (continuando sem CVD):', error.message);
      return data;
    }
  }
}

// Instância global
const autoEnricher = new AutoEnricher();

// ===== INTERCEPTAR FUNCTION EXISTENTE =====
// Salvar a função processJSON original
const originalProcessJSON = window.processJSON;

// Substituir pela versão que enriquece
if (typeof originalProcessJSON === 'function') {
  window.processJSON = async function(data) {
    // Enriquecer com CVD antes de processar
    const enriched = await autoEnricher.enrich(data);
    
    // Chamar a função original com dados enriquecidos
    return originalProcessJSON(enriched);
  };
  
  console.log('✅ Auto-enriquecimento CVD ativado — carregue o JSON normalmente');
}
