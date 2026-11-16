"use strict";
var __makeTemplateObject = (this && this.__makeTemplateObject) || function (cooked, raw) {
    if (Object.defineProperty) { Object.defineProperty(cooked, "raw", { value: raw }); } else { cooked.raw = raw; }
    return cooked;
};
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.register = void 0;
var NAME = { five_hour: 'session', seven_day: 'weekly' };
var TOKEN = String.raw(templateObject_1 || (templateObject_1 = __makeTemplateObject(["(?<![w./-])/(session|weekly)-token-utilization(?![w-])"], ["(?<![\\w./-])\\/(session|weekly)-token-utilization(?![\\w-])"
    // "until /session-token-utilization gets to 90%": "until" through the percentage.
])));
// "until /session-token-utilization gets to 90%": "until" through the percentage.
var CLAUSE = new RegExp(String.raw(templateObject_2 || (templateObject_2 = __makeTemplateObject(["(?:\buntils+)?", "(?:[^\n/%]*?(d+(?:.d+)?)s*%)?"], ["(?:\\buntil\\s+)?", "(?:[^\\n/%]*?(\\d+(?:\\.\\d+)?)\\s*%)?"])), TOKEN), 'gi');
var FORM = 'token-utilization: name a percentage from 1 to 100, e.g. "until /session-token-utilization gets to 90%". Prompt not sent.';
var IMMEDIATE = 'Stop immediately';
var WRAP = 'Wrap up first';
var YES = 'Yes, run it';
var ACTIVE = ['pending', 'running', 'waiting'];
function parse(text) {
    var limits = [];
    var bad = false;
    var marked = text.replace(CLAUSE, function (_m, window, n) {
        var percent = Number(n);
        if (!n || !(percent >= 1 && percent <= 100))
            bad = true;
        limits.push({ kind: window.toLowerCase() === 'session' ? 'five_hour' : 'seven_day', percent: percent });
        return '\0';
    });
    var rest = marked
        .replace(/\0(?:\s*,?\s*(?:\bor\b|\band\b)?\s*\0)+/gi, '\0') // "… or /weekly-…": one gap
        .replace(/\s*\0\s*([.,;:!?])/g, '$1')
        .replace(/\0/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    return { limits: limits, rest: rest, bad: bad };
}
var now = function (readings, kind) { var _a; return (_a = readings.find(function (w) { return w.kind === kind; })) === null || _a === void 0 ? void 0 : _a.percentUsed; };
var at = function (l, readings) {
    var p = now(readings, l.kind);
    return "".concat(NAME[l.kind], " ").concat(l.percent, "% (").concat(p === undefined ? 'no reading yet' : "now ".concat(p, "%"), ")");
};
function statusText(s, readings) {
    if (!s)
        return undefined;
    if (s.phase === 'armed')
        return "stop at ".concat(s.limits.map(function (l) { return at(l, readings); }).join(' or '), ", ").concat(s.mode);
    if (s.phase === 'wrapping')
        return "wrapping up, cut off at ".concat(at(s.ceiling, readings));
    return s.ceiling ? "stopped, subagents cut off at ".concat(at(s.ceiling, readings)) : 'stopped at the usage limit';
}
var stateKey = function ($) { return __awaiter(void 0, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
    switch (_b.label) {
        case 0:
            _a = "s:".concat;
            return [4 /*yield*/, $.session.id()];
        case 1: return [2 /*return*/, _a.apply("s:", [_b.sent()])];
    }
}); }); };
var turnKey = function ($) { return __awaiter(void 0, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
    switch (_b.label) {
        case 0:
            _a = "t:".concat;
            return [4 /*yield*/, $.session.id()];
        case 1: return [2 /*return*/, _a.apply("t:", [_b.sent()])];
    }
}); }); };
var readingsOf = function ($) { return __awaiter(void 0, void 0, void 0, function () { return __generator(this, function (_a) {
    switch (_a.label) {
        case 0: return [4 /*yield*/, $.session.usage()];
        case 1: return [2 /*return*/, (_a.sent()).rateLimits];
    }
}); }); };
var debug = function ($, text) { return $.ui.log("token-utilization: ".concat(text), { to: 'debug' }); };
var handoffPath = function ($) { return __awaiter(void 0, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
    switch (_b.label) {
        case 0:
            _a = ".claude/handoffs/HANDOFF-".concat;
            return [4 /*yield*/, $.session.id()];
        case 1: return [2 /*return*/, _a.apply(".claude/handoffs/HANDOFF-", [(_b.sent()).slice(0, 8), ".md"])];
    }
}); }); };
function load($) {
    return __awaiter(this, void 0, void 0, function () {
        var _a, _b;
        return __generator(this, function (_c) {
            switch (_c.label) {
                case 0:
                    _b = (_a = $.store).get;
                    return [4 /*yield*/, stateKey($)];
                case 1: return [4 /*yield*/, _b.apply(_a, [_c.sent()])];
                case 2: return [2 /*return*/, (_c.sent())];
            }
        });
    });
}
function save($, s, readings) {
    return __awaiter(this, void 0, void 0, function () {
        var key, _a, _b, _c, _d, _e;
        return __generator(this, function (_f) {
            switch (_f.label) {
                case 0: return [4 /*yield*/, stateKey($)];
                case 1:
                    key = _f.sent();
                    if (!s) return [3 /*break*/, 3];
                    return [4 /*yield*/, $.store.set(key, s)];
                case 2:
                    _f.sent();
                    return [3 /*break*/, 5];
                case 3: return [4 /*yield*/, $.store.delete(key)];
                case 4:
                    _f.sent();
                    _f.label = 5;
                case 5:
                    _b = (_a = $.ui).status;
                    _c = statusText;
                    _d = [s];
                    if (!(readings !== null && readings !== void 0)) return [3 /*break*/, 6];
                    _e = readings;
                    return [3 /*break*/, 8];
                case 6: return [4 /*yield*/, readingsOf($)];
                case 7:
                    _e = (_f.sent());
                    _f.label = 8;
                case 8:
                    _b.apply(_a, [_c.apply(void 0, _d.concat([_e]))]);
                    return [2 /*return*/];
            }
        });
    });
}
var activeAgents = function ($) { return __awaiter(void 0, void 0, void 0, function () { return __generator(this, function (_a) {
    switch (_a.label) {
        case 0: return [4 /*yield*/, $.agent.list()];
        case 1: return [2 /*return*/, (_a.sent()).filter(function (a) { return ACTIVE.includes(a.status); })
            // Cancels the main turn and stops every running subagent; the state is saved first, so the
            // notifications those stops raise are recognised as the mod's own.
        ];
    }
}); }); };
// Cancels the main turn and stops every running subagent; the state is saved first, so the
// notifications those stops raise are recognised as the mod's own.
function stopAll($, s, readings) {
    return __awaiter(this, void 0, void 0, function () {
        var agents, turnId, _a, _b, _i, agents_1, a, r;
        var _c;
        return __generator(this, function (_d) {
            switch (_d.label) {
                case 0: return [4 /*yield*/, activeAgents($)];
                case 1:
                    agents = _d.sent();
                    Object.assign(s, { phase: 'stopped', ceiling: undefined, inject: undefined, wrapTurnId: undefined });
                    s.stoppedIds = __spreadArray(__spreadArray([], ((_c = s.stoppedIds) !== null && _c !== void 0 ? _c : []), true), agents.map(function (a) { return a.id; }), true);
                    return [4 /*yield*/, save($, s, readings)];
                case 2:
                    _d.sent();
                    _b = (_a = $.store).get;
                    return [4 /*yield*/, turnKey($)];
                case 3: return [4 /*yield*/, _b.apply(_a, [_d.sent()])];
                case 4:
                    turnId = (_d.sent());
                    if (!turnId) return [3 /*break*/, 6];
                    return [4 /*yield*/, $.turn.abort({ turnId: turnId }).catch(function (err) { return debug($, "abort failed: ".concat(err)); })];
                case 5:
                    _d.sent();
                    _d.label = 6;
                case 6:
                    _i = 0, agents_1 = agents;
                    _d.label = 7;
                case 7:
                    if (!(_i < agents_1.length)) return [3 /*break*/, 10];
                    a = agents_1[_i];
                    return [4 /*yield*/, $.tool.call({ tool: 'TaskStop', task_id: a.id }).catch(function (err) { return ({ deny: String(err) }); })];
                case 8:
                    r = _d.sent();
                    if ('deny' in r && r.deny !== undefined)
                        debug($, "TaskStop ".concat(a.id, " failed: ").concat(r.deny));
                    _d.label = 9;
                case 9:
                    _i++;
                    return [3 /*break*/, 7];
                case 10: return [2 /*return*/];
            }
        });
    });
}
function mainText(label, interrupted, subagents, path, cutoff) {
    var first = interrupted
        ? "You were interrupted because ".concat(label, ", the limit set for this task.")
        : "".concat(label[0].toUpperCase()).concat(label.slice(1), ", the limit set for this task.");
    return [
        "".concat(first, " Wrap up now:"),
        '',
        '- If only a little work is left, finish it.',
        '- Otherwise stop here and leave the work easy to continue.',
        '',
        "Do not start new work.".concat(subagents ? ' Subagents received the same instruction; collect what they report.' : ''),
        'End with handoff notes as your final message: what is done, what is in progress, what is left,',
        "and the exact next step. That message is saved to ".concat(path, "; to resume later, read that file first. Usage is cut off at ").concat(cutoff, "%."),
    ].join('\n');
}
var subText = function (label, cutoff) {
    return "".concat(label[0].toUpperCase()).concat(label.slice(1), ", the limit set for this task. Wrap up now: if only a little work is ") +
        'left, finish it. Otherwise stop here and report what is done, what is in progress and what is ' +
        "left. Do not start new work. Usage is cut off at ".concat(cutoff, "%.");
};
function trip($, s, limit, readings) {
    return __awaiter(this, void 0, void 0, function () {
        var label, ceiling, turnId, _a, _b, agents, path, next, _i, agents_2, a, r;
        var _c;
        return __generator(this, function (_d) {
            switch (_d.label) {
                case 0:
                    label = "".concat(NAME[limit.kind], " usage reached ").concat(limit.percent, "%");
                    if (!(s.mode === 'immediate')) return [3 /*break*/, 2];
                    return [4 /*yield*/, stopAll($, s, readings)];
                case 1:
                    _d.sent();
                    $.ui.log("token-utilization: ".concat(label, ", stopped"));
                    return [2 /*return*/];
                case 2:
                    ceiling = { kind: limit.kind, percent: Math.min(100, limit.percent + 5) };
                    _b = (_a = $.store).get;
                    return [4 /*yield*/, turnKey($)];
                case 3: return [4 /*yield*/, _b.apply(_a, [_d.sent()])];
                case 4:
                    turnId = (_d.sent());
                    return [4 /*yield*/, activeAgents($)];
                case 5:
                    agents = _d.sent();
                    return [4 /*yield*/, handoffPath($)];
                case 6:
                    path = _d.sent();
                    if (!!agents.length) return [3 /*break*/, 11];
                    if (!!turnId) return [3 /*break*/, 8];
                    return [4 /*yield*/, save($, __assign(__assign({}, s), { phase: 'stopped' }), readings)];
                case 7:
                    _d.sent();
                    $.ui.log("token-utilization: ".concat(label, ", stopped"));
                    return [2 /*return*/];
                case 8: return [4 /*yield*/, save($, __assign(__assign({}, s), { phase: 'wrapping', ceiling: ceiling }), readings)];
                case 9:
                    _d.sent();
                    return [4 /*yield*/, $.turn.abort({ turnId: turnId }).catch(function (err) { return debug($, "abort failed: ".concat(err)); })];
                case 10:
                    _d.sent();
                    void $.prompt.submit({ text: mainText(label, true, false, path, ceiling.percent) }).catch(function (err) { return debug($, "submit failed: ".concat(err)); });
                    $.ui.log("token-utilization: ".concat(label, ", wrapping up; cut off at ").concat(ceiling.percent, "%"));
                    return [2 /*return*/];
                case 11:
                    next = __assign(__assign({}, s), { ceiling: ceiling, messagedIds: __spreadArray(__spreadArray([], ((_c = s.messagedIds) !== null && _c !== void 0 ? _c : []), true), agents.map(function (a) { return a.id; }), true) });
                    if (turnId)
                        Object.assign(next, { phase: 'wrapping', wrapTurnId: turnId, inject: mainText(label, false, true, path, ceiling.percent) });
                    else
                        next.phase = 'stopped';
                    return [4 /*yield*/, save($, next, readings)];
                case 12:
                    _d.sent();
                    _i = 0, agents_2 = agents;
                    _d.label = 13;
                case 13:
                    if (!(_i < agents_2.length)) return [3 /*break*/, 16];
                    a = agents_2[_i];
                    return [4 /*yield*/, $.session.send({ to: { agentId: a.id }, text: subText(label, ceiling.percent) }).catch(function (err) { return ({ isDelivered: false, reason: String(err) }); })];
                case 14:
                    r = _d.sent();
                    if (!r.isDelivered)
                        debug($, "wrap-up message to ".concat(a.id, " not delivered: ").concat(r.reason));
                    _d.label = 15;
                case 15:
                    _i++;
                    return [3 /*break*/, 13];
                case 16:
                    $.ui.log("token-utilization: ".concat(label, ", ").concat(turnId ? 'wrapping up' : 'stopped; subagents wrapping up', "; cut off at ").concat(ceiling.percent, "%"));
                    return [2 /*return*/];
            }
        });
    });
}
// A prompt or command line naming a limit: undefined when it names none, else the text without
// the limit phrase, or the reason to refuse it.
function arm($, text) {
    return __awaiter(this, void 0, void 0, function () {
        var _a, limits, rest, bad, readings, _i, limits_1, l, p, answer;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0:
                    _a = parse(text), limits = _a.limits, rest = _a.rest, bad = _a.bad;
                    if (!limits.length)
                        return [2 /*return*/, undefined];
                    if (bad)
                        return [2 /*return*/, { drop: FORM }];
                    return [4 /*yield*/, readingsOf($)];
                case 1:
                    readings = _b.sent();
                    for (_i = 0, limits_1 = limits; _i < limits_1.length; _i++) {
                        l = limits_1[_i];
                        p = now(readings, l.kind);
                        if (p !== undefined && p >= l.percent) {
                            return [2 /*return*/, { drop: "token-utilization: ".concat(NAME[l.kind], " usage is already at ").concat(p, "%, past the ").concat(l.percent, "% limit. Prompt not sent.") }];
                        }
                    }
                    return [4 /*yield*/, $.ui.ask('What should happen when the limit is reached?', [IMMEDIATE, WRAP]).catch(function () { return undefined; })];
                case 2:
                    answer = _b.sent();
                    if (answer !== IMMEDIATE && answer !== WRAP)
                        return [2 /*return*/, { drop: 'token-utilization: no stop mode chosen. Prompt not sent.' }];
                    return [4 /*yield*/, save($, { limits: limits, mode: answer === IMMEDIATE ? 'immediate' : 'wrap-up', phase: 'armed' }, readings)];
                case 3:
                    _b.sent();
                    return [2 /*return*/, { rest: rest }];
            }
        });
    });
}
var isTyped = function (o) { return o.kind === 'composer' || o.kind === 'bridge'; };
// A -p prompt naming a limit is handled like a typed one (and dropped, as nobody can be asked).
var mayArm = function (o) { return isTyped(o) || o.kind === 'sdk'; };
var register = function (on) {
    on('session.start', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var _a, _b;
        return __generator(this, function (_c) {
            switch (_c.label) {
                case 0: return [4 /*yield*/, $.command.register({
                        name: 'token-utilization',
                        description: 'Show the usage limit set for this session, or remove it with off',
                        argumentHint: '[off]',
                    })];
                case 1:
                    _c.sent();
                    _a = save;
                    _b = [$];
                    return [4 /*yield*/, load($)];
                case 2: return [4 /*yield*/, _a.apply(void 0, _b.concat([_c.sent()]))]; // redraw the status after a reload or a resume
                case 3:
                    _c.sent(); // redraw the status after a reload or a resume
                    return [2 /*return*/, next(e)];
            }
        });
    }); });
    on('turn.start', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var _a, _b, s;
        return __generator(this, function (_c) {
            switch (_c.label) {
                case 0:
                    if (!(e.agentId === undefined)) return [3 /*break*/, 5];
                    _b = (_a = $.store).set;
                    return [4 /*yield*/, turnKey($)];
                case 1: return [4 /*yield*/, _b.apply(_a, [_c.sent(), e.turnId])];
                case 2:
                    _c.sent();
                    return [4 /*yield*/, load($)];
                case 3:
                    s = _c.sent();
                    if (!((s === null || s === void 0 ? void 0 : s.phase) === 'wrapping' && !s.wrapTurnId)) return [3 /*break*/, 5];
                    return [4 /*yield*/, save($, __assign(__assign({}, s), { wrapTurnId: e.turnId }))];
                case 4:
                    _c.sent();
                    _c.label = 5;
                case 5: return [2 /*return*/, next(e)];
            }
        });
    }); });
    on('turn.complete', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var r, key, s, path, root, readings_1, missing;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, next(e)];
                case 1:
                    r = _a.sent();
                    if (e.agentId !== undefined)
                        return [2 /*return*/, r];
                    return [4 /*yield*/, turnKey($)];
                case 2:
                    key = _a.sent();
                    return [4 /*yield*/, $.store.get(key)];
                case 3:
                    if (!((_a.sent()) === e.turnId)) return [3 /*break*/, 5];
                    return [4 /*yield*/, $.store.delete(key)];
                case 4:
                    _a.sent();
                    _a.label = 5;
                case 5: return [4 /*yield*/, load($)];
                case 6:
                    s = _a.sent();
                    if (!((s === null || s === void 0 ? void 0 : s.wrapTurnId) === e.turnId)) return [3 /*break*/, 12];
                    return [4 /*yield*/, handoffPath($)];
                case 7:
                    path = _a.sent();
                    return [4 /*yield*/, $.session.root()];
                case 8:
                    root = _a.sent();
                    return [4 /*yield*/, $.fs.write("".concat(root, "/").concat(path), r.text)];
                case 9:
                    _a.sent();
                    return [4 /*yield*/, $.fs.write("".concat(root, "/.claude/handoffs/.gitignore"), '*\n')];
                case 10:
                    _a.sent();
                    return [4 /*yield*/, save($, __assign(__assign({}, s), { phase: 'stopped', wrapTurnId: undefined, inject: undefined }))];
                case 11:
                    _a.sent();
                    $.ui.log("token-utilization: handoff notes saved to ".concat(path));
                    return [3 /*break*/, 15];
                case 12:
                    if (!((s === null || s === void 0 ? void 0 : s.phase) === 'armed' && !s.warned)) return [3 /*break*/, 15];
                    return [4 /*yield*/, readingsOf($)];
                case 13:
                    readings_1 = _a.sent();
                    missing = s.limits.filter(function (l) { return now(readings_1, l.kind) === undefined; });
                    if (!missing.length) return [3 /*break*/, 15];
                    $.ui.log("token-utilization: no ".concat(missing.map(function (l) { return NAME[l.kind]; }).join(' or '), " usage reading yet, so the limit cannot take effect"));
                    return [4 /*yield*/, save($, __assign(__assign({}, s), { warned: true }), readings_1)];
                case 14:
                    _a.sent();
                    _a.label = 15;
                case 15: return [2 /*return*/, r];
            }
        });
    }); });
    // The main agent's wrap-up text while subagents run: read with its next tool result, once.
    on('tool.call', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var r, s;
        var _a;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0: return [4 /*yield*/, next(e)];
                case 1:
                    r = _b.sent();
                    if (e.agentId !== undefined || e.tool === 'AskUserQuestion' || ('deny' in r && r.deny !== undefined))
                        return [2 /*return*/, r];
                    return [4 /*yield*/, load($)];
                case 2:
                    s = _b.sent();
                    if (!(s === null || s === void 0 ? void 0 : s.inject))
                        return [2 /*return*/, r];
                    return [4 /*yield*/, save($, __assign(__assign({}, s), { inject: undefined }))];
                case 3:
                    _b.sent();
                    return [2 /*return*/, __assign(__assign({}, r), { context: __spreadArray(__spreadArray([], ((_a = r.context) !== null && _a !== void 0 ? _a : []), true), [s.inject], false) })];
            }
        });
    }); });
    on('prompt.submit', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var o, r, s, id, sent, err_1, answer;
        var _a, _b, _c, _d;
        return __generator(this, function (_e) {
            switch (_e.label) {
                case 0:
                    o = e.origin;
                    if ((o.kind === 'plugin' && o.name === $.plugin.name) || ((_a = e.command) === null || _a === void 0 ? void 0 : _a.name) === 'token-utilization')
                        return [2 /*return*/, next(e)
                            // A slash command's limit is handled at command.run, which runs first.
                        ];
                    if (!(!e.command && mayArm(o))) return [3 /*break*/, 2];
                    return [4 /*yield*/, arm($, e.text)];
                case 1:
                    r = _e.sent();
                    if (r && 'drop' in r)
                        return [2 /*return*/, { drop: r.drop }];
                    if (r)
                        return [2 /*return*/, next(__assign(__assign({}, e), { text: r.rest }))];
                    _e.label = 2;
                case 2: return [4 /*yield*/, load($)];
                case 3:
                    s = _e.sent();
                    if (!s)
                        return [2 /*return*/, next(e)];
                    if (!isTyped(o)) return [3 /*break*/, 6];
                    if (!(s.phase !== 'armed')) return [3 /*break*/, 5];
                    return [4 /*yield*/, save($, undefined)]; // a typed prompt ends the wrap-up or the stop
                case 4:
                    _e.sent(); // a typed prompt ends the wrap-up or the stop
                    _e.label = 5;
                case 5: // a typed prompt ends the wrap-up or the stop
                return [2 /*return*/, next(e)];
                case 6:
                    if (s.phase !== 'stopped')
                        return [2 /*return*/, next(e)];
                    if (o.kind === 'task-notification') {
                        id = (_b = /<task-id>([^<]+)<\/task-id>/.exec(e.text)) === null || _b === void 0 ? void 0 : _b[1];
                        if (id && ((_c = s.stoppedIds) === null || _c === void 0 ? void 0 : _c.includes(id)))
                            return [2 /*return*/, { drop: 'token-utilization: dropped the notification of a subagent it stopped.' }];
                        if (id && ((_d = s.messagedIds) === null || _d === void 0 ? void 0 : _d.includes(id)))
                            return [2 /*return*/, next(e)];
                    }
                    _e.label = 7;
                case 7:
                    _e.trys.push([7, 9, , 10]);
                    return [4 /*yield*/, $.ui.notify('An automatic prompt is waiting for your answer', { title: 'token-utilization' })];
                case 8:
                    sent = _e.sent();
                    if (!sent.isSent)
                        debug($, "notification not sent: ".concat(sent.reason));
                    return [3 /*break*/, 10];
                case 9:
                    err_1 = _e.sent();
                    debug($, "notification not sent: ".concat(err_1));
                    return [3 /*break*/, 10];
                case 10: return [4 /*yield*/, $.ui.ask('The usage limit was reached. Run this automatic prompt?', [YES, 'No']).catch(function () { return undefined; })];
                case 11:
                    answer = _e.sent();
                    if (answer !== YES)
                        return [2 /*return*/, { drop: 'token-utilization: automatic prompt not run, the usage limit was reached.' }];
                    return [4 /*yield*/, save($, undefined)];
                case 12:
                    _e.sent();
                    return [2 /*return*/, next(e)];
            }
        });
    }); });
    on('command.run', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var arg, s, readings_2, r;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (!(e.command === 'token-utilization')) return [3 /*break*/, 5];
                    arg = e.args.trim().toLowerCase();
                    if (!(arg === 'off')) return [3 /*break*/, 2];
                    return [4 /*yield*/, save($, undefined)];
                case 1:
                    _a.sent();
                    return [2 /*return*/, { text: 'token-utilization: limit removed.' }];
                case 2:
                    if (arg)
                        return [2 /*return*/, { text: 'Usage: /token-utilization [off]' }];
                    return [4 /*yield*/, load($)];
                case 3:
                    s = _a.sent();
                    if (!s)
                        return [2 /*return*/, { text: 'token-utilization: no limit is set.' }];
                    return [4 /*yield*/, readingsOf($)];
                case 4:
                    readings_2 = _a.sent();
                    return [2 /*return*/, { text: "token-utilization: ".concat(s.limits.map(function (l) { return at(l, readings_2); }).join(' or '), ", mode ").concat(s.mode, ", ").concat(s.phase, ".") }];
                case 5:
                    if (!mayArm(e.origin)) return [3 /*break*/, 7];
                    return [4 /*yield*/, arm($, e.args)];
                case 6:
                    r = _a.sent();
                    if (r && 'drop' in r)
                        return [2 /*return*/, { text: r.drop }];
                    if (r)
                        return [2 /*return*/, next(__assign(__assign({}, e), { args: r.rest }))];
                    _a.label = 7;
                case 7: return [2 /*return*/, next(e)];
            }
        });
    }); });
    on('session.measure', function ($, e, next) { return __awaiter(void 0, void 0, void 0, function () {
        var s, readings, reached, hit, c;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, load($)];
                case 1:
                    s = _a.sent();
                    readings = e.rateLimits;
                    reached = function (l) { var _a; return ((_a = now(readings, l.kind)) !== null && _a !== void 0 ? _a : -1) >= l.percent; };
                    if (!((s === null || s === void 0 ? void 0 : s.phase) === 'armed')) return [3 /*break*/, 6];
                    hit = s.limits.find(reached);
                    if (!hit) return [3 /*break*/, 3];
                    return [4 /*yield*/, trip($, s, hit, readings)];
                case 2:
                    _a.sent();
                    return [3 /*break*/, 5];
                case 3: return [4 /*yield*/, save($, s, readings)];
                case 4:
                    _a.sent();
                    _a.label = 5;
                case 5: return [3 /*break*/, 10];
                case 6:
                    if (!((s === null || s === void 0 ? void 0 : s.ceiling) && reached(s.ceiling))) return [3 /*break*/, 8];
                    c = s.ceiling;
                    return [4 /*yield*/, stopAll($, s, readings)];
                case 7:
                    _a.sent();
                    $.ui.log("token-utilization: ".concat(NAME[c.kind], " usage reached ").concat(c.percent, "% during the wrap-up, stopped"));
                    return [3 /*break*/, 10];
                case 8:
                    if (!s) return [3 /*break*/, 10];
                    return [4 /*yield*/, save($, s, readings)];
                case 9:
                    _a.sent();
                    _a.label = 10;
                case 10: return [2 /*return*/, next(e)];
            }
        });
    }); });
};
exports.register = register;
var templateObject_1, templateObject_2;
