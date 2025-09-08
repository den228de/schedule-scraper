// Telegram Web App JavaScript
class ScheduleApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupTelegramTheme();
        this.loadSchedule();
        this.setupEventListeners();
    }

    setupTelegramTheme() {
        // Проверяем, запущено ли приложение в Telegram
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            
            // Применяем тему Telegram
            document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
            document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#1a1a1a');
            document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
            document.documentElement.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
            document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
            document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
            document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f8f9fa');
        }
    }

    async loadSchedule() {
        try {
            this.showLoading();
            
            // Добавляем логирование для отладки
            console.log('Загружаем расписание...');
            
            const response = await fetch('/api/versions');
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const versions = await response.json();
            console.log('Получены версии:', versions);
            
            if (versions.length > 0) {
                // Ищем версию с данными (не пустую)
                let versionToUse = null;
                for (let i = 0; i < versions.length; i++) {
                    const version = versions[i];
                    console.log(`Проверяем версию ${version.id}:`, version);
                    
                    // Проверяем, есть ли данные в этой версии
                    const scheduleResponse = await fetch(`/api/schedule/${version.id}`);
                    if (scheduleResponse.ok) {
                        const scheduleData = await scheduleResponse.json();
                        if (scheduleData && scheduleData.length > 0) {
                            versionToUse = version;
                            console.log('Найдена версия с данными:', versionToUse);
                            this.renderSchedule(scheduleData, version.week_start);
                            break;
                        }
                    }
                }
                
                if (!versionToUse) {
                    this.showEmptyState();
                }
            } else {
                this.showEmptyState();
            }
        } catch (error) {
            console.error('Error loading schedule:', error);
            this.showError(`Ошибка загрузки расписания: ${error.message}`);
        }
    }

    renderSchedule(scheduleData, weekStart) {
        const container = document.querySelector('.schedule-container');
        container.innerHTML = '';

        // Группируем занятия по дням
        const days = this.groupByDays(scheduleData);
        
        if (Object.keys(days).length === 0) {
            this.showEmptyState();
            return;
        }

        // Сортируем дни по дате
        const sortedDays = Object.keys(days).sort((a, b) => {
            const dateA = this.parseDate(a);
            const dateB = this.parseDate(b);
            return dateA - dateB;
        });

        sortedDays.forEach(dateStr => {
            const dayCard = this.createDayCard(dateStr, days[dateStr]);
            container.appendChild(dayCard);
        });

        this.hideLoading();
    }

        groupByDays(scheduleData) {
        const days = {};
        
        scheduleData.forEach(item => {
            const subject = item.subject || '';
            const dateMatch = subject.match(/(\d{2}\.\d{2}\.\d{4})/);
            
            if (dateMatch) {
                const dateStr = dateMatch[1];
                if (!days[dateStr]) {
                    days[dateStr] = [];
                }
                days[dateStr].push(item);
            }
        });
        
        // Сортируем пары внутри каждого дня по номеру пары
        Object.keys(days).forEach(dateStr => {
            days[dateStr].sort((a, b) => {
                const pairA = a.pair || 0;
                const pairB = b.pair || 0;
                return pairA - pairB;
            });
        });
        
        return days;
    }

    createDayCard(dateStr, lessons) {
        const dayCard = document.createElement('div');
        dayCard.className = 'day-card';
        
        const dateObj = this.parseDate(dateStr);
        const weekday = this.getWeekdayName(dateObj);
        
        dayCard.innerHTML = `
            <div class="day-header">
                <div class="day-title">${weekday}</div>
                <div class="day-date">${this.formatDate(dateStr)}</div>
            </div>
            <div class="lessons">
                ${lessons.map((lesson, index) => this.createLessonItem(lesson, index + 1)).join('')}
            </div>
        `;
        
        return dayCard;
    }

    createLessonItem(lesson, number) {
        const time = lesson.time || '';
        const subject = lesson.subject || '';
        const room = lesson.room || '';
        const kind = lesson.kind || '';
        const pair = lesson.pair || number;
        const teacher = lesson.teacher || '';
        
        // Определяем тип занятия по полю kind
        let lessonType = '';
        if (kind === 'Лекция') {
            lessonType = 'Лекция';
        } else if (kind === 'Лабораторная') {
            lessonType = 'Лабораторная';
        } else if (kind === 'Семинар') {
            lessonType = 'Семинар';
        } else if (kind === 'Зачет') {
            lessonType = 'Зачет';
        } else {
            lessonType = 'Практика';
        }
        
        // Очищаем название предмета - убираем дату, преподавателя И тип занятия
        let cleanSubject = subject;
        // Убираем дату и день недели из начала
        cleanSubject = cleanSubject.replace(/^\d{2}\.\d{2}\.\d{4}\s+[А-Яа-я]+-\d+\s*\|\s*/, '');
        // Убираем тип занятия в скобках в конце (например: "(Лекция)", "(Практич.)")
        cleanSubject = cleanSubject.replace(/\s*\([^)]+\)\s*$/, '');
        
        // Определяем класс для иконки типа занятия
        const typeIconClass = lessonType === 'Практика' ? 'icon-type practice' : 'icon-type';
        
        return `
            <div class="lesson-item">
                <div class="lesson-content">
                    <div class="lesson-header">
                        <div class="lesson-subject">${cleanSubject}</div>
                        <div class="lesson-time">${time}</div>
                    </div>
                    <div class="lesson-details">
                        ${room ? `<div class="lesson-detail"><span class="icon-room"></span> ${room}</div>` : ''}
                        ${lessonType ? `<div class="lesson-detail"><span class="${typeIconClass}"></span> ${lessonType}</div>` : ''}
                        ${teacher ? `<div class="lesson-detail"><span class="icon-teacher"></span> ${teacher}</div>` : ''}
                        <div class="lesson-detail"><span class="icon-pair"></span> Пара ${pair}</div>
                    </div>
                </div>
            </div>
        `;
    }

    parseDate(dateStr) {
        const [day, month, year] = dateStr.split('.');
        return new Date(year, month - 1, day);
    }

    getWeekdayName(date) {
        const weekdays = [
            'Воскресенье', 'Понедельник', 'Вторник', 'Среда', 
            'Четверг', 'Пятница', 'Суббота'
        ];
        return weekdays[date.getDay()];
    }
    
    formatDate(dateStr) {
        const [day, month, year] = dateStr.split('.');
        const months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ];
        return `${day} ${months[parseInt(month) - 1]} ${year}`;
    }

    showLoading() {
        const container = document.querySelector('.schedule-container');
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <div>Загружаем расписание...</div>
            </div>
        `;
    }

    hideLoading() {
        const loading = document.querySelector('.loading');
        if (loading) {
            loading.remove();
        }
    }

    showEmptyState() {
        const container = document.querySelector('.schedule-container');
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Расписание пока не загружено</h3>
                <p>Ожидается первый прогон скрапера</p>
            </div>
        `;
    }

    showError(message) {
        const container = document.querySelector('.schedule-container');
        container.innerHTML = `
            <div class="empty-state">
                <div>❌</div>
                <h3>Ошибка</h3>
                <p>${message}</p>
            </div>
        `;
    }

    setupEventListeners() {
        // Кнопка обновления
        const refreshBtn = document.querySelector('.fab-button');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadSchedule();
            });
        }

        // Анимация появления карточек
        this.animateCards();
    }

    animateCards() {
        const cards = document.querySelectorAll('.day-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new ScheduleApp();
});

// Обработка ошибок
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

// Обработка необработанных промисов
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});
