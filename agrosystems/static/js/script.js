document.addEventListener('DOMContentLoaded', function () {
    // Получение элемента модального окна
    var modal = document.getElementById("myModal");

    // Получение элемента <span>, который закрывает модальное окно
    var span = document.getElementsByClassName("close")[0];

    // Получение кнопки, которая открывает модальное окно
    var btn = document.getElementById("addProjectButton");

    // Когда пользователь кликает на кнопку, открыть модальное окно
    btn.onclick = function () {
        modal.style.display = "block";
    }

    // Когда пользователь кликает на <span> (x), закрыть модальное окно
    span.onclick = function () {
        modal.style.display = "none";
    }

    // Когда пользователь кликает в любом месте за пределами модального окна, закрыть его
    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

});


