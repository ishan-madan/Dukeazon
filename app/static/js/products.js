document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('top-k-form');
  const input = document.getElementById('top-k-input');
  const alertBox = document.getElementById('top-k-alert');
  const resultsContainer = document.getElementById('top-k-results');

  if (!form) {
    return;
  }

  const productTitleMap = {
    'vanilla ice cream': 'Vanilla Ice Cream',
    'chocolate ice cream': 'Chocolate Ice Cream',
    'strawberry ice cream': 'Strawberry Ice Cream',
    '6-pack of paycheck pilsners': '6-Pack of Paycheck Pilsners',
    'seven fabergé easter eggs': 'Seven Fabergé Easter Eggs',
    'painting - the storm on the sea of galilee': 'Painting: The Storm on the Sea of Galilee'
  };

  const currencyFormatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  });

  const formatProductName = (name) => {
    if (!name) {
      return '';
    }
    const normalized = name.toLowerCase();
    return productTitleMap[normalized] || name;
  };

  const renderResults = (products) => {
    const table = document.createElement('table');
    table.className = 'table table-striped table-hover mt-3';

    const rows = products.length
      ? products.map((product) => {
          const priceNumber = Number(product.price);
          const formattedPrice = Number.isFinite(priceNumber)
            ? currencyFormatter.format(priceNumber)
            : product.price;
          return `
            <tr>
              <th scope="row">${product.id}</th>
              <td>${formatProductName(product.name)}</td>
              <td class="text-right">${formattedPrice}</td>
            </tr>`;
        }).join('')
      : `<tr><td colspan="3" class="text-center text-muted">No products found for this selection.</td></tr>`;

    table.innerHTML = `
      <thead class="thead-dark">
        <tr>
          <th scope="col">Product ID</th>
          <th scope="col">Product Name</th>
          <th scope="col" class="text-right">Price</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    `;
    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(table);
  };

  const renderError = (message) => {
    alertBox.textContent = message;
  };

  const clearMessages = () => {
    alertBox.textContent = '';
    resultsContainer.innerHTML = '';
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearMessages();

    const rawValue = input.value;
    const k = Number(rawValue);

    if (!Number.isInteger(k) || k <= 0) {
      renderError('Please enter a positive integer for k.');
      return;
    }

    try {
      const response = await fetch(`/products/top?k=${k}`);
      const payload = await response.json();
      if (!response.ok) {
        renderError(payload.error || 'Unable to fetch products.');
        return;
      }
      renderResults(payload.products || []);
    } catch (error) {
      renderError('Unexpected error fetching products.');
    }
  });
});
