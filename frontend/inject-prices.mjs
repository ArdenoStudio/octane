import { readFileSync, writeFileSync } from 'fs';

const FUEL_LABELS = {
  petrol_92: 'Petrol 92 Octane',
  petrol_95: 'Petrol 95 Octane',
  auto_diesel: 'Auto Diesel',
  super_diesel: 'Super Diesel',
  kerosene: 'Kerosene',
};

const FUEL_ORDER = ['petrol_92', 'petrol_95', 'auto_diesel', 'super_diesel', 'kerosene'];

async function main() {
  let prices = [];
  let lastUpdated = '';

  try {
    const res = await fetch('https://d2w9pgvodb18rj.cloudfront.net/v1/prices/latest');
    const data = await res.json();
    const cpcPrices = data.prices.filter((p) => p.source === 'cpc');
    prices = FUEL_ORDER.map((fuel) => cpcPrices.find((p) => p.fuel_type === fuel)).filter(Boolean);
    lastUpdated = prices[0]?.recorded_at ?? '';
  } catch (e) {
    console.warn('inject-prices: failed to fetch prices, skipping injection:', e.message);
    return;
  }

  const html = readFileSync('dist/index.html', 'utf8');

  const priceItems = prices
    .map((p) => `<li>${FUEL_LABELS[p.fuel_type]}: LKR ${p.price_lkr} per litre</li>`)
    .join('\n        ');

  const noscriptBlock = `  <noscript>
    <div id="seo-prices" style="max-width:800px;margin:40px auto;padding:20px;font-family:sans-serif">
      <h1>Sri Lanka Fuel Prices Today</h1>
      <p>Current Sri Lanka petrol and diesel prices tracked by <a href="https://octane-smoky.vercel.app">Octane</a>:</p>
      <ul>
        ${priceItems}
      </ul>
      <p>Prices sourced from Ceylon Petroleum Corporation (CEYPETCO). Last updated: ${lastUpdated}.</p>
      <p>Octane provides live Sri Lanka fuel price tracking, price history charts, world price comparison, trip cost calculator, and a free public API.</p>
    </div>
  </noscript>`;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Octane',
    url: 'https://octane-smoky.vercel.app',
    description:
      'Live Sri Lanka fuel prices, history charts, world comparison, trip cost calculator, and a free public API. Built by Ardeno Studio.',
    publisher: {
      '@type': 'Organization',
      name: 'Ardeno Studio',
      url: 'https://ardeno.studio',
    },
    potentialAction: {
      '@type': 'SearchAction',
      target: 'https://octane-smoky.vercel.app/#prices',
    },
    mainEntity: {
      '@type': 'ItemList',
      name: 'Sri Lanka Fuel Prices',
      description: `Current fuel prices in Sri Lanka as of ${lastUpdated}`,
      itemListElement: prices.map((p, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: FUEL_LABELS[p.fuel_type],
        description: `${FUEL_LABELS[p.fuel_type]} price in Sri Lanka: LKR ${p.price_lkr} per litre as of ${p.recorded_at}`,
      })),
    },
  };

  const newJsonLd = `<script type="application/ld+json">\n    ${JSON.stringify(jsonLd, null, 6).replace(/\n/g, '\n    ')}\n    </script>`;

  let updated = html.replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/, newJsonLd);
  updated = updated.replace('</body>', `${noscriptBlock}\n  </body>`);

  writeFileSync('dist/index.html', updated);
  console.log(`inject-prices: injected ${prices.length} prices (last updated ${lastUpdated})`);
}

main();
