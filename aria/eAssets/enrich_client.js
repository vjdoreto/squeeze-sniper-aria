/**
 * Integração automática de enriquecimento CVD
 * Injete esse script no HTML do dashboard
 * 
 * Funcionamento:
 * 1. Quando usuário faz upload de JSON
 * 2. Envia para http://127.0.0.1:5001/api/enrich-json
 * 3. Retorna JSON com CVD enriquecido
 * 4. Dashboard renderiza com dados CVD
 */

class CVDEnricher {
  constructor(serverUrl = 'http://127.0.0.1:5001/api/enrich-json') {
    this.serverUrl = serverUrl;
    this.isAvailable = false;
    this.checkServerAvailability();
  }

  async checkServerAvailability() {
    try {
      const response = await fetch('http://127.0.0.1:5001/health');
      this.isAvailable = response.ok;
      if (this.isAvailable) {
        console.log('✅ Servidor de enriquecimento disponível');
      }
    } catch (e) {
      console.warn('⚠️  Servidor de enriquecimento indisponível — modo fallback');
      this.isAvailable = false;
    }
  }

  async enrich(panelData) {
    console.log('📤 Enviando dados para enriquecimento...');
    console.log('   Símbolos no painel:', Object.keys(panelData.data || panelData).slice(0, 10));
    
    if (!this.isAvailable) {
      console.log('ℹ️  Usando dados sem CVD (servidor indisponível)');
      return panelData;
    }

    try {
      const response = await fetch(this.serverUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(panelData)
      });

      if (response.ok) {
        const enriched = await response.json();
        console.log(`✅ Enriquecido: ${enriched.enriched_symbols} símbolos com CVD`);
        return enriched;
      } else {
        console.error(`❌ Erro enriquecendo: ${response.status}`);
        return panelData;
      }
    } catch (error) {
      console.error('❌ Erro chamando servidor:', error);
      return panelData;
    }
  }
}

// Instância global
const cvdEnricher = new CVDEnricher();

/**
 * Hook para integração com o dashboard existente
 * 
 * Adicione após o carregamento do JSON:
 * 
 * // Quando o usuário faz upload do JSON:
 * const panelData = JSON.parse(fileContent);
 * const enriched = await cvdEnricher.enrich(panelData);
 * // Usar 'enriched' em vez de 'panelData'
 */

// AUTO-INTEGRAÇÃO (opcional)
// Se você quer enriquecer automaticamente sem mudar o código existente,
// intercepte o evento de upload/carga:

(function() {
  const originalFetch = window.fetch;
  
  // Monitorar carregamentos de JSON
  window.addEventListener('message', async (e) => {
    if (e.data.type === 'LOAD_PANEL_JSON') {
      const panelData = e.data.payload;
      const enriched = await cvdEnricher.enrich(panelData);
      
      // Disparar evento com dados enriquecidos
      window.postMessage({
        type: 'PANEL_JSON_ENRICHED',
        payload: enriched
      }, '*');
    }
  });
})();
