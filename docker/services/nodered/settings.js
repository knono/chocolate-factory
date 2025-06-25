/**
 * TFM Chocolate Factory - Node-RED Settings
 * ===========================================
 * 
 * Configuración para El Monitor (Dashboard Read-Only)
 * - Solo visualización de datos
 * - Sin ejecución de acciones
 * - Conexiones a InfluxDB y MLflow
 */

module.exports = {
    // Puerto de Node-RED (ya gestionado por Docker)
    uiPort: process.env.PORT || 1880,
    
    // Directorio de flujos y datos
    userDir: '/data',
    flowFile: 'flows.json',
    
    // Configuración de logging
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },
    
    // Deshabilitar el editor para hacer read-only
    disableEditor: false, // Para desarrollo, cambiar a true en producción
    
    // Configuración de la interfaz web
    httpAdminRoot: '/',
    httpNodeRoot: '/dashboard',
    
    // Seguridad básica (para producción)
    adminAuth: {
        type: "credentials",
        users: [{
            username: "admin",
            password: "$2b$08$zZWtXTja0fB1pzD4sHCMyOCMYz2Z6dNbM6tl8sJogENOMcxWV9DN.", // "password"
            permissions: "*"
        }]
    },
    
    // Variables de entorno disponibles en Node-RED
    functionGlobalContext: {
        // Conexiones a servicios
        influxdb_url: process.env.INFLUXDB_URL || 'http://influxdb:8086',
        influxdb_token: process.env.INFLUXDB_TOKEN,
        influxdb_org: process.env.INFLUXDB_ORG,
        influxdb_bucket: process.env.INFLUXDB_BUCKET,
        mlflow_url: process.env.MLFLOW_URL || 'http://mlflow:5000'
    },
    
    // Paleta de nodos disponibles
    nodesIncludes: ['*'],
    
    // Editor settings
    editorTheme: {
        projects: {
            enabled: false
        },
        page: {
            title: "TFM Chocolate Factory - El Monitor"
        },
        header: {
            title: "🍫 Chocolate Factory Monitor",
            url: "about:blank"
        }
    }
};