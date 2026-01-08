function showExcludeUI(id) {
  if (!id) {
    var el = document.getElementById('excludeUI');
    if (el) el.classList.remove('d-none');
    return;
  }
  var el2 = document.getElementById(id);
  if (el2) el2.classList.remove('d-none');
}
