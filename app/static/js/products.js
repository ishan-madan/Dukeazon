document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('top-k-form');
  const input = document.getElementById('top-k-input');
  const alertBox = document.getElementById('top-k-alert');
  const resultsContainer = document.getElementById('top-k-results');

  if (!form) {
    return;
  }

  const renderResults = (products) => {
    if (!products.length) {
      resultsContainer.innerHTML = '<p>No products found.</p>';
      return;
    }

    const table = document.createElement('table');
    table.className = 'table table-hover table-bordered';

    table.innerHTML = `
      <thead class="thead-dark">
        <tr>
          <th scope="col">Product ID</th>
          <th scope="col">Product Name</th>
          <th scope="col">Price</th>
        </tr>
      </thead>
      <tbody>
        ${products.map(
          (product) => `
            <tr>
              <th scope="row">${product.id}</th>
              <td>${product.name}</td>
              <td>${product.price.toFixed(2)}</td>
            </tr>`
        ).join('')}
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
