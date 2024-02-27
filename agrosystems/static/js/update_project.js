function deleteProject(projectId) {
    // Получаем CSRF-токен из куки
    const csrftoken = getCookie('csrftoken');

    fetch(`/delete-project/${projectId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrftoken  // Добавляем CSRF-токен в заголовок запроса
        }
    })
    .then(response => {
        if (response.ok) {
            updateProjects(); // Обновляем список проектов
        } else {
            alert("Ошибка при удалении проекта.");
        }
    })
    .catch(error => console.error('Ошибка:', error));
}

// Функция для получения CSRF-токена из куки
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


function updateProjects() {
    $.ajax({
        url: '/',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            var projects = response.projects;
            var projectsList = $('#projectsList');
            projectsList.empty(); // Clear the current list of projects
            projects.forEach(function(project) {
                var buttons = '';
                if (project.status === 'Complete') {
                    var viewMapUrl = `/view-map/${project.id}`; // Предполагается, что у вас есть такой URL-паттерн
                    buttons = `
                        <div class="project-actions">
                            <button onclick="location.href='${viewMapUrl}'">View Map</button>
                            <button onclick="deleteProject(${project.id})">Delete</button>
                        </div>
                    `;
                } else if (project.status === 'Error') {
                    buttons = `
                        <div class="project-actions">
                            <button onclick="deleteProject(${project.id})">Delete</button>
                        </div>
                    `;
                }
                projectsList.append(`
                    <div class="project">
                        <h3>${project.project_name}</h3>
                        <p>Model type: ${project.model_type}</p>
                        <p>Status: ${project.status}</p>
                        ${buttons}
                    </div>
                `);
            });
        }
    });
}



$(document).ready(function() {
    // Update the list of projects immediately on page load
    updateProjects();

    // Update the list of projects every 5 seconds
    setInterval(updateProjects, 5000);
});
