pipeline {
    agent any

    environment {
        FINNHUB_API_KEY = credentials('finnhub_api_key')
        SENDGRID_API_KEY = credentials('sendgrid_api_key')
        SENDGRID_SENDER  = credentials('sendgrid_sender')
        ALERT_EMAIL      = credentials('alert_email')
    }

    // Ejecutar automáticamente todos los días a las 8h (cron)
    triggers {
        cron('H 8 * * *')
    }

    stages {
        stage('Install dependencies') {
            steps {
                // Instalamos las librerías Python necesarias usando --break-system-packages
                sh 'python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt'
            }
        }

        stage('Run Buyback Detector') {
            steps {
                sh '''
                    # Crear notified.json si no existe
                    if [ ! -f "$WORKSPACE/notified.json" ]; then
                        echo '{}' > $WORKSPACE/notified.json
                    fi
                    # Ejecutar el script de detección de recompras
                    python3 scripts/check_buybacks_finnhub.py
                '''
            }
        }
    }

    post {
        success {
            // Guardar notified.json para próximas ejecuciones
            archiveArtifacts artifacts: 'notified.json', allowEmptyArchive: true
            echo 'Pipeline finalizado correctamente.'
        }
        failure {
            echo 'Pipeline falló. Revisa los logs.'
        }
    }
}
