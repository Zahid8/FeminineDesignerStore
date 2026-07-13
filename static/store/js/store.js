// FemDes storefront progressive enhancements
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5s
    document.querySelectorAll('.alert').forEach(function (el) {
      setTimeout(function () { el.style.transition = 'opacity .5s'; el.style.opacity = '0'; setTimeout(function () { el.remove(); }, 500); }, 5000);
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        var target = document.querySelector(this.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });

    // Product gallery thumbnail click → main image switch
    document.querySelectorAll('.product-thumb').forEach(function (thumb) {
      thumb.addEventListener('click', function () {
        var main = document.getElementById('main-product-image');
        if (main) { main.src = this.src; }
      });
    });

    // Quantity +/- steppers (adds quick adjust buttons)
    document.querySelectorAll('.product-qty input[type="number"]').forEach(function (input) {
      var wrapper = document.createElement('div');
      wrapper.className = 'd-flex align-items-center gap-1';
      input.parentNode.insertBefore(wrapper, input);
      var minus = document.createElement('button');
      minus.type = 'button'; minus.textContent = '−'; minus.className = 'btn btn-sm btn-outline-dark';
      minus.addEventListener('click', function () { if (input.value > 1) input.value = parseInt(input.value) - 1; });
      var plus = document.createElement('button');
      plus.type = 'button'; plus.textContent = '+'; plus.className = 'btn btn-sm btn-outline-dark';
      plus.addEventListener('click', function () { input.value = parseInt(input.value) + 1; });
      wrapper.appendChild(minus); wrapper.appendChild(input); wrapper.appendChild(plus);
    });
  });
})();
