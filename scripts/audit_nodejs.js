#!/usr/bin/env node
/**
 * Script de Auditoria de Dependências Node.js/React
 * 
 * Este script verifica vulnerabilidades conhecidas em todas as dependências
 * Node.js do projeto usando npm audit.
 * 
 * Uso:
 *   node scripts/audit_nodejs.js [--json] [--fix] [--production]
 * 
 * Opções:
 *   --json          Gera relatório em JSON
 *   --fix           Tenta corrigir vulnerabilidades automaticamente
 *   --production    Audita apenas dependências de produção
 *   --severity      Filtra por severidade mínima (low, moderate, high, critical)
 * 
 * Retorna:
 *   0 - Nenhuma vulnerabilidade encontrada
 *   1 - Vulnerabilidades encontradas
 *   2 - Erro na execução
 * 
 * Exemplo:
 *   node scripts/audit_nodejs.js --severity high --production
 */

const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const util = require('util');

const execPromise = util.promisify(exec);

// Cores ANSI para terminal
const Colors = {
    RED: '\x1b[91m',
    GREEN: '\x1b[92m',
    YELLOW: '\x1b[93m',
    BLUE: '\x1b[94m',
    MAGENTA: '\x1b[95m',
    CYAN: '\x1b[96m',
    BOLD: '\x1b[1m',
    RESET: '\x1b[0m'
};

function printHeader(message) {
    console.log(`\n${Colors.BOLD}${Colors.CYAN}${'='.repeat(80)}${Colors.RESET}`);
    console.log(`${Colors.BOLD}${Colors.CYAN}${message.padStart((80 + message.length) / 2).padEnd(80)}${Colors.RESET}`);
    console.log(`${Colors.BOLD}${Colors.CYAN}${'='.repeat(80)}${Colors.RESET}\n`);
}

function printSuccess(message) {
    console.log(`${Colors.GREEN}✓ ${message}${Colors.RESET}`);
}

function printError(message) {
    console.log(`${Colors.RED}✗ ${message}${Colors.RESET}`);
}

function printWarning(message) {
    console.log(`${Colors.YELLOW}⚠ ${message}${Colors.RESET}`);
}

function printInfo(message) {
    console.log(`${Colors.BLUE}ℹ ${message}${Colors.RESET}`);
}

async function checkNpmInstalled() {
    try {
        await execPromise('npm --version');
        return true;
    } catch (error) {
        return false;
    }
}

async function runNpmAudit(options = {}) {
    /**
     * Executa npm audit
     * 
     * @param {Object} options - Opções de auditoria
     * @param {boolean} options.json - Output em JSON
     * @param {boolean} options.fix - Corrigir automaticamente
     * @param {boolean} options.production - Apenas produção
     * @param {string} options.severity - Severidade mínima
     * @returns {Promise<Object>} Resultado da auditoria
     */
    
    let cmd = 'npm audit';
    
    if (options.json) {
        cmd += ' --json';
    }
    
    if (options.production) {
        cmd += ' --production';
    }
    
    if (options.severity) {
        cmd += ` --audit-level=${options.severity}`;
    }
    
    printInfo(`Executando: ${cmd}`);
    
    try {
        const { stdout, stderr } = await execPromise(cmd, {
            cwd: path.join(__dirname, '..', '..', 'evento-site'),
            maxBuffer: 10 * 1024 * 1024 // 10MB buffer
        });
        
        return {
            exitCode: 0,
            stdout: stdout,
            stderr: stderr
        };
    } catch (error) {
        // npm audit retorna exit code 1 se encontrar vulnerabilidades
        return {
            exitCode: error.code || 1,
            stdout: error.stdout || '',
            stderr: error.stderr || ''
        };
    }
}

async function runNpmAuditFix(production = false) {
    /**
     * Executa npm audit fix para corrigir vulnerabilidades
     * 
     * @param {boolean} production - Apenas dependências de produção
     * @returns {Promise<Object>} Resultado da correção
     */
    
    let cmd = 'npm audit fix';
    
    if (production) {
        cmd += ' --production';
    }
    
    printInfo(`Executando: ${cmd}`);
    
    try {
        const { stdout, stderr } = await execPromise(cmd, {
            cwd: path.join(__dirname, '..', '..', 'evento-site'),
            maxBuffer: 10 * 1024 * 1024
        });
        
        return {
            exitCode: 0,
            stdout: stdout,
            stderr: stderr
        };
    } catch (error) {
        return {
            exitCode: error.code || 1,
            stdout: error.stdout || '',
            stderr: error.stderr || ''
        };
    }
}

function parseAuditOutput(jsonOutput) {
    /**
     * Parseia output JSON do npm audit
     * 
     * @param {string} jsonOutput - Output em JSON
     * @returns {Object|null} Dados parseados
     */
    try {
        return JSON.parse(jsonOutput);
    } catch (error) {
        printError(`Erro ao parsear JSON: ${error.message}`);
        return null;
    }
}

function analyzeSeverity(auditData) {
    /**
     * Analisa severidade das vulnerabilidades
     * 
     * @param {Object} auditData - Dados da auditoria
     * @returns {Object} Estatísticas de severidade
     */
    
    const stats = {
        info: 0,
        low: 0,
        moderate: 0,
        high: 0,
        critical: 0,
        total: 0
    };
    
    if (auditData.metadata && auditData.metadata.vulnerabilities) {
        const vulns = auditData.metadata.vulnerabilities;
        stats.info = vulns.info || 0;
        stats.low = vulns.low || 0;
        stats.moderate = vulns.moderate || 0;
        stats.high = vulns.high || 0;
        stats.critical = vulns.critical || 0;
        stats.total = vulns.total || 0;
    }
    
    return stats;
}

function generateReport(auditData, outputFile = 'audit_reports/nodejs_audit.json') {
    /**
     * Gera relatório de auditoria
     * 
     * @param {Object} auditData - Dados da auditoria
     * @param {string} outputFile - Arquivo de saída
     */
    
    const report = {
        timestamp: new Date().toISOString(),
        tool: 'npm audit',
        project: 'evento-site',
        audit_data: auditData,
        severity_stats: analyzeSeverity(auditData)
    };
    
    // Criar diretório de relatórios
    const outputPath = path.join(__dirname, '..', outputFile);
    const outputDir = path.dirname(outputPath);
    
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2), 'utf-8');
    printSuccess(`Relatório salvo em: ${outputFile}`);
}

function printSummary(exitCode, auditData) {
    /**
     * Imprime resumo da auditoria
     * 
     * @param {number} exitCode - Código de saída
     * @param {Object} auditData - Dados da auditoria
     */
    
    printHeader('RESUMO DA AUDITORIA NODE.JS/REACT');
    
    if (exitCode === 0) {
        printSuccess('Nenhuma vulnerabilidade conhecida encontrada!');
        printInfo('Todas as dependências Node.js/React estão seguras.');
    } else if (exitCode === 1) {
        printWarning('VULNERABILIDADES ENCONTRADAS!');
        
        if (auditData) {
            const stats = analyzeSeverity(auditData);
            console.log('\nEstatísticas de Severidade:');
            console.log(`${Colors.MAGENTA}Critical:${Colors.RESET} ${stats.critical}`);
            console.log(`${Colors.RED}High:${Colors.RESET}     ${stats.high}`);
            console.log(`${Colors.YELLOW}Moderate:${Colors.RESET} ${stats.moderate}`);
            console.log(`${Colors.BLUE}Low:${Colors.RESET}      ${stats.low}`);
            console.log(`${Colors.CYAN}Info:${Colors.RESET}     ${stats.info}`);
            console.log(`${Colors.BOLD}Total:${Colors.RESET}    ${stats.total}\n`);
            
            // Listar vulnerabilidades críticas e altas
            if (auditData.vulnerabilities) {
                const highSeverity = Object.entries(auditData.vulnerabilities)
                    .filter(([, vuln]) => vuln.severity === 'critical' || vuln.severity === 'high')
                    .slice(0, 10); // Limitar a 10 para não poluir o output
                
                if (highSeverity.length > 0) {
                    console.log(`${Colors.BOLD}Top vulnerabilidades críticas/altas:${Colors.RESET}`);
                    highSeverity.forEach(([pkg, vuln]) => {
                        const color = vuln.severity === 'critical' ? Colors.MAGENTA : Colors.RED;
                        console.log(`  ${color}[${vuln.severity.toUpperCase()}]${Colors.RESET} ${pkg}`);
                        if (vuln.via && vuln.via.length > 0) {
                            const issue = vuln.via[0];
                            if (typeof issue === 'object') {
                                console.log(`    ${issue.title || 'No title'}`);
                                console.log(`    ${issue.url || ''}`);
                            }
                        }
                    });
                }
            }
        }
    } else {
        printError('ERRO NA EXECUÇÃO DA AUDITORIA!');
    }
    
    console.log(`\n${Colors.BOLD}Exit code: ${exitCode}${Colors.RESET}`);
}

function shouldFailDeploy(auditData, failOn) {
    /**
     * Determina se o deploy deve falhar baseado na severidade
     * 
     * @param {Object} auditData - Dados da auditoria
     * @param {string} failOn - Nível de falha (any, high, critical)
     * @returns {boolean} True se deve falhar
     */
    
    if (failOn === 'any') {
        return true; // Qualquer vulnerabilidade bloqueia
    }
    
    const stats = analyzeSeverity(auditData);
    
    if (failOn === 'critical') {
        return stats.critical > 0;
    }
    
    if (failOn === 'high') {
        return stats.high > 0 || stats.critical > 0;
    }
    
    return false;
}

async function main() {
    const args = process.argv.slice(2);
    
    const options = {
        json: args.includes('--json'),
        fix: args.includes('--fix'),
        production: args.includes('--production'),
        severity: null,
        failOn: 'any'
    };
    
    // Parse --severity
    const severityIndex = args.indexOf('--severity');
    if (severityIndex !== -1 && args[severityIndex + 1]) {
        options.severity = args[severityIndex + 1];
    }
    
    // Parse --fail-on
    const failOnIndex = args.indexOf('--fail-on');
    if (failOnIndex !== -1 && args[failOnIndex + 1]) {
        options.failOn = args[failOnIndex + 1];
    }
    
    printHeader('AUDITORIA DE DEPENDÊNCIAS NODE.JS/REACT');
    printInfo(`Projeto: evento-site`);
    printInfo(`Data: ${new Date().toLocaleString()}`);
    
    // Verificar se npm está instalado
    if (!await checkNpmInstalled()) {
        printError('npm não está instalado!');
        return 2;
    }
    
    // Aplicar correções se solicitado
    if (options.fix) {
        printInfo('Tentando corrigir vulnerabilidades...');
        const fixResult = await runNpmAuditFix(options.production);
        console.log(fixResult.stdout);
        if (fixResult.stderr) {
            printWarning(fixResult.stderr);
        }
    }
    
    // Executar auditoria
    const result = await runNpmAudit(options);
    
    let auditData = null;
    
    // Parsear JSON se disponível
    if (result.stdout) {
        if (options.json || result.stdout.trim().startsWith('{')) {
            auditData = parseAuditOutput(result.stdout);
            if (auditData && options.json) {
                generateReport(auditData);
            }
        } else {
            // Output em texto
            console.log(result.stdout);
        }
    }
    
    if (result.stderr && !result.stderr.includes('npm WARN')) {
        printError(result.stderr);
    }
    
    // Imprimir resumo
    printSummary(result.exitCode, auditData);
    
    // Determinar se deve falhar o deploy
    if (result.exitCode === 1 && auditData) {
        if (shouldFailDeploy(auditData, options.failOn)) {
            printError('Deploy BLOQUEADO: Vulnerabilidades encontradas');
            return 1;
        } else {
            printWarning('Deploy PERMITIDO: Vulnerabilidades abaixo do limite configurado');
            return 0;
        }
    }
    
    return result.exitCode;
}

// Executar se chamado diretamente
if (require.main === module) {
    main()
        .then(exitCode => process.exit(exitCode))
        .catch(error => {
            printError(`Erro fatal: ${error.message}`);
            console.error(error);
            process.exit(2);
        });
}

module.exports = { runNpmAudit, analyzeSeverity, generateReport };
