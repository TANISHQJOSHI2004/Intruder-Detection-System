const registerBtn = document.querySelector('.register-btn');
const registerExtra = document.getElementById('registerExtra');

registerBtn.addEventListener('click', () => {
    registerExtra.classList.toggle('show');
});
