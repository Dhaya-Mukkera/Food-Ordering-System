document.addEventListener('DOMContentLoaded', function () {
  // auto-hide success/info messages
  document.querySelectorAll('.alert[data-auto]').forEach(function (a) {
    setTimeout(function () { a.classList.remove('show'); setTimeout(function () { a.remove(); }, 300); }, 4500);
  });
  // confirm dialogs for dangerous actions: <form data-confirm="Are you sure?">
  document.querySelectorAll('form[data-confirm]').forEach(function (f) {
    f.addEventListener('submit', function (e) { if (!confirm(f.dataset.confirm)) e.preventDefault(); });
  });
  // image preview in the food form
  var input = document.getElementById('image'), prev = document.getElementById('imgPreview');
  if (input && prev) input.addEventListener('change', function () {
    if (input.files && input.files[0]) prev.src = URL.createObjectURL(input.files[0]);
  });
});
