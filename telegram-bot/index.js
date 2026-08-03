import 'dotenv/config';
import { Telegraf } from 'telegraf';
import axios from 'axios';
import express from 'express';

const bot = new Telegraf(process.env.BOT_TOKEN || 'dummy');
const NOCODB_URL = process.env.NOCODB_URL || 'http://nocodb:8080';
const NOCODB_TOKEN = process.env.NOCODB_TOKEN || '';
const CHAT_ID = process.env.CHAT_ID || '';

const api = axios.create({
  baseURL: NOCODB_URL,
  headers: { 'xc-token': NOCODB_TOKEN }
});

function autorizado(ctx) {
  return String(ctx.chat.id) === CHAT_ID;
}

bot.start((ctx) => {
  if (!autorizado(ctx)) return ctx.reply('No autorizado.');
  ctx.reply(
    'VerifiCuba Bot\n\n' +
    '/negocios - Ultimos 10\n' +
    '/pendientes - Sin verificar\n' +
    '/stats - Estadisticas\n' +
    '/buscar <texto> - Buscar'
  );
});

bot.command('negocios', async (ctx) => {
  if (!autorizado(ctx)) return;
  try {
    const { data } = await api.get('/api/v2/tables/negocios/records', {
      params: { limit: 10, sort: '-fecha_registro' }
    });
    if (!data.list || !data.list.length) {
      return ctx.reply('No hay negocios registrados.');
    }
    const msg = data.list.map((n, i) =>
      (i+1) + '. ' + (n.nombre || 'Sin nombre') +
      '\n   ' + (n.provincia || '') + ', ' + (n.municipio || '') +
      '\n   ' + (n.whatsapp || '') +
      '\n   Estado: ' + (n.estado || 'Pendiente')
    ).join('\n\n');
    ctx.reply('Ultimos negocios:\n\n' + msg);
  } catch (e) {
    console.error(e.message);
    ctx.reply('Error consultando NocoDB. Verifica el token.');
  }
});

bot.command('pendientes', async (ctx) => {
  if (!autorizado(ctx)) return;
  try {
    const { data } = await api.get('/api/v2/tables/negocios/records', {
      params: { limit: 50, where: '(estado,eq,Pendiente)', sort: '-fecha_registro' }
    });
    if (!data.list || !data.list.length) {
      return ctx.reply('No hay pendientes. Todo verificado.');
    }
    const msg = data.list.map((n, i) =>
      (i+1) + '. ' + (n.nombre || '') + ' - ' + (n.provincia || '') + ' - ' + (n.whatsapp || '')
    ).join('\n');
    ctx.reply(data.list.length + ' pendientes:\n\n' + msg);
  } catch (e) {
    ctx.reply('Error consultando NocoDB.');
  }
});

bot.command('stats', async (ctx) => {
  if (!autorizado(ctx)) return;
  try {
    const total = await api.get('/api/v2/tables/negocios/records', { params: { limit: 1 } })
      .then(r => r.data.pageInfo.totalRows).catch(() => 0);
    const verif = await api.get('/api/v2/tables/negocios/records', { params: { where: '(estado,eq,Verificado)', limit: 1 } })
      .then(r => r.data.pageInfo.totalRows).catch(() => 0);
    const pend = await api.get('/api/v2/tables/negocios/records', { params: { where: '(estado,eq,Pendiente)', limit: 1 } })
      .then(r => r.data.pageInfo.totalRows).catch(() => 0);

    ctx.reply(
      'VerifiCuba Stats\n\n' +
      'Total: ' + total + '\n' +
      'Verificados: ' + verif + '\n' +
      'Pendientes: ' + pend + '\n\n' +
      'Ingresos est.: ' + (verif * 500) + ' CUP/mes'
    );
  } catch (e) {
    ctx.reply('Error generando stats.');
  }
});

bot.command('buscar', async (ctx) => {
  if (!autorizado(ctx)) return;
  const query = ctx.message.text.split(' ').slice(1).join(' ');
  if (!query) return ctx.reply('Uso: /buscar <nombre>');
  try {
    const { data } = await api.get('/api/v2/tables/negocios/records', {
      params: { limit: 10, where: '(nombre,like,%' + query + '%)' }
    });
    if (!data.list || !data.list.length) {
      return ctx.reply('Sin resultados para "' + query + '"');
    }
    const msg = data.list.map(n =>
      n.nombre + ' - ' + (n.municipio || '') + ', ' + (n.provincia || '') + ' - ' + (n.estado || '')
    ).join('\n');
    ctx.reply('Resultados:\n\n' + msg);
  } catch (e) {
    ctx.reply('Error en busqueda.');
  }
});

// Webhook server
const app = express();
app.use(express.json());

app.post('/webhook/nuevo-negocio', async (req, res) => {
  const n = req.body;
  if (!n || !n.nombre) return res.status(400).send('Missing data');
  const msg =
    'Nuevo pre-registro\n\n' +
    'Negocio: ' + n.nombre + '\n' +
    'Ubicacion: ' + (n.municipio || '') + ', ' + (n.provincia || '') + '\n' +
    'WhatsApp: ' + (n.whatsapp || 'Sin WhatsApp') + '\n' +
    'Tipo: ' + (n.tipo_actor || 'No especificado') + '\n\n' +
    new Date().toLocaleString('es-CU');
  try {
    if (CHAT_ID) {
      await bot.telegram.sendMessage(CHAT_ID, msg);
    }
    res.json({ ok: true });
  } catch (e) {
    console.error('Webhook error:', e.message);
    res.status(500).json({ error: e.message });
  }
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

const PORT = 3000;
app.listen(PORT, () => console.log('Webhook server on port ' + PORT));

if (process.env.BOT_TOKEN) {
  bot.launch().then(() => console.log('Bot iniciado'));
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));
} else {
  console.log('Sin BOT_TOKEN. Solo webhook server activo.');
}
