document.addEventListener('DOMContentLoaded', function() {
    // Create more dynamic bubbles
    const container = document.body;
    for (let i = 0; i < 5; i++) {
        const bubble = document.createElement('div');
        bubble.classList.add('bubble');
        
        // Random size between 40 and 120px
        const size = Math.random() * 80 + 40;
        bubble.style.width = `${size}px`;
        bubble.style.height = `${size}px`;
        
        // Random position
        bubble.style.left = `${Math.random() * 100}%`;
        bubble.style.top = `${Math.random() * 100}%`;
        
        // Random animation
        const duration = Math.random() * 7 + 5;
        const delay = Math.random() * 5;
        bubble.style.animation = `float ${duration}s ease-in-out infinite ${delay}s`;
        
        container.appendChild(bubble);
    }
    
    // Form validation
    const form = document.querySelector('form');
    form.id = 'loginForm';
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const user_id = document.getElementById('user_id').value; 
        const password = document.getElementById('password').value;

        if (!user_id || !password) {
            alert('Please fill in all fields');
            return;
        }
        
        // Here you would typically send the data to a server
        // Send login request to server
        fetch('/admin_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user_id,
                password: password
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert(data.message || 'Login successful!');
                // Redirect to admin dashboard
                window.location.href = '/admin_dashboard';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during login');
        });
    });
});