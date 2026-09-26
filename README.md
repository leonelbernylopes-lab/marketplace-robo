# Marketplace Resale Hunter V1

Robô local para monitorar o Facebook Marketplace e filtrar oportunidades de revenda.

## O que esta V1 faz
- Abre o Facebook Marketplace em um navegador Chromium persistente.
- Você faz login manualmente no Facebook.
- Busca uma lista de termos configurada em `config.json`.
- Extrai preço, título, localização e link dos cards visíveis.
- Elimina duplicados.
- Aplica preço máximo e distância quando disponíveis.
- Calcula um preço de revenda de referência usando `resale_prices.json`.
- Calcula lucro e margem estimados.
- Gera `opportunities.csv` e `opportunities.json`.
- Mostra as melhores oportunidades no terminal.

## Limitações
O Facebook pode alterar a estrutura da página, exigir verificações ou limitar automação. Esta V1 não tenta burlar CAPTCHA, bloqueios ou controles de acesso. Se o Facebook pedir uma verificação, faça-a manualmente.

## Instalação no Windows

1. Instale Python 3.11+.
2. Abra o PowerShell nesta pasta.
3. Execute:
   `python -m venv .venv`
4. Ative:
   `.venv\Scripts\Activate.ps1`
5. Instale:
   `pip install -r requirements.txt`
6. Instale o navegador do Playwright:
   `python -m playwright install chromium`
7. Edite `config.json`.
8. Execute:
   `python main.py`

Na primeira execução, uma janela do Chromium será aberta. Faça login manualmente no Facebook. A sessão fica salva na pasta `browser_profile`.

## Configuração

`config.json`:
- `search_terms`: produtos que o robô deve procurar.
- `max_buy_price`: preço máximo de compra.
- `min_profit`: lucro mínimo estimado.
- `min_margin`: margem mínima estimada.
- `search_radius_km`: referência de distância; o Marketplace pode não expor distância em todos os cards.
- `scrolls_per_search`: quantas vezes rolar cada busca.
- `headless`: deixe false para a V1.
- `delay_seconds`: pausa entre ações.

`resale_prices.json` contém referências simples. Exemplo:
- PS4 Slim 500GB: compra interessante até R$ 550; revenda de referência R$ 850.
- Air fryer 4L: revenda de referência R$ 180.

Para começar com R$ 1.000, recomendo testar poucos produtos e registrar os preços reais de venda. Depois podemos substituir essa tabela por um modelo que aprende com seus próprios negócios.

## Resultado

Os resultados ficam em:
- `opportunities.csv`
- `opportunities.json`

A coluna `score` vai de 0 a 100 e é apenas um índice técnico da configuração, não uma garantia de venda.
