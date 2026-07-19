-- Lectern Sync 1.3.1
-- One-way Fantasy Grounds Unity 5E export. This script never writes FG database nodes.

local EXTENSION_VERSION = "1.3.1"
local SCHEMA_VERSION = 1
local bExporting = false
local tCachedSnapshot = nil
local nSequence = 0
local JSON_NULL = {}
local aEventJournal = {}
local nEventSequence = 0
local sCombatSessionKey = nil
local sCombatSessionName = nil
local sSessionStartedAt = nil
local sSessionState = "inactive"
local sOutcome = nil
local sCompletedAt = nil
local tLastCombatants = {}
local sLastActiveKey = nil
local bHaveCombatBaseline = false
local bLastCombatActive = false
local tLastRollContext = nil
local bHaveAuthoritativeAttackHook = false
local bWarnedNoSession = false
local saveSessionState = nil
local sPersistedEventsJSON = ""
local nPersistedJournalCount = 0

local tFallbackMappings = {
  class = { "class", "reference.classdata", "reference.classes" },
  subclass = { "subclass", "specialization", "reference.subclassdata", "reference.specializationdata", "reference.subclasses" },
  race = { "race", "reference.racedata", "reference.races" },
  feat = { "feat", "reference.featdata", "reference.feats" },
  background = { "background", "reference.backgrounddata", "reference.backgrounds" },
  battle = { "battle", "reference.battledata", "reference.battles" },
}

local function chat(sText)
  Comm.addChatMessage({ text = sText, sender = "Lectern Sync", font = "systemfont" })
end

local function isoTimestamp()
  if os and os.date then
    return os.date("!%Y-%m-%dT%H:%M:%SZ")
  end
  return "1970-01-01T00:00:00Z"
end

local function jsonEscape(sValue)
  local s = tostring(sValue or "")
  s = s:gsub("\\", "\\\\")
  s = s:gsub('"', '\\"')
  s = s:gsub("\b", "\\b")
  s = s:gsub("\f", "\\f")
  s = s:gsub("\n", "\\n")
  s = s:gsub("\r", "\\r")
  s = s:gsub("\t", "\\t")
  s = s:gsub("[%z\1-\31]", function(c) return string.format("\\u%04x", string.byte(c)) end)
  return s
end

local function isArray(tValue)
  if type(tValue) ~= "table" then return false end
  local nCount = 0
  local nMaximum = 0
  for k, _ in pairs(tValue) do
    if type(k) ~= "number" or k < 1 or k ~= math.floor(k) then return false end
    nCount = nCount + 1
    if k > nMaximum then nMaximum = k end
  end
  return nCount == nMaximum
end

local function encodeJSON(vValue, tSeen)
  if vValue == JSON_NULL then return "null" end
  local sType = type(vValue)
  if sType == "nil" then return "null" end
  if sType == "boolean" then return vValue and "true" or "false" end
  if sType == "number" then
    if vValue ~= vValue or vValue == math.huge or vValue == -math.huge then return "null" end
    return tostring(vValue)
  end
  if sType == "string" then return '"' .. jsonEscape(vValue) .. '"' end
  if sType ~= "table" then return '"' .. jsonEscape(tostring(vValue)) .. '"' end

  tSeen = tSeen or {}
  if tSeen[vValue] then return '"[circular]"' end
  tSeen[vValue] = true
  local aParts = {}
  if isArray(vValue) then
    for i = 1, #vValue do table.insert(aParts, encodeJSON(vValue[i], tSeen)) end
    tSeen[vValue] = nil
    return "[" .. table.concat(aParts, ",") .. "]"
  end
  local aKeys = {}
  for k, _ in pairs(vValue) do table.insert(aKeys, tostring(k)) end
  table.sort(aKeys)
  for _, sKey in ipairs(aKeys) do
    table.insert(aParts, '"' .. jsonEscape(sKey) .. '":' .. encodeJSON(vValue[sKey], tSeen))
  end
  tSeen[vValue] = nil
  return "{" .. table.concat(aParts, ",") .. "}"
end

local function extractArrayContents(sJSON, sKey)
  local sMarker = '"' .. sKey .. '":['
  local nMarker = sJSON and sJSON:find(sMarker, 1, true) or nil
  if not nMarker then return "" end
  local nStart = nMarker + #sMarker
  local nDepth = 1
  local bInString = false
  local bEscaped = false
  for nIndex = nStart, #sJSON do
    local sChar = sJSON:sub(nIndex, nIndex)
    if bInString then
      if bEscaped then bEscaped = false
      elseif sChar == "\\" then bEscaped = true
      elseif sChar == '"' then bInString = false end
    else
      if sChar == '"' then bInString = true
      elseif sChar == "[" then nDepth = nDepth + 1
      elseif sChar == "]" then
        nDepth = nDepth - 1
        if nDepth == 0 then return sJSON:sub(nStart, nIndex - 1) end
      end
    end
  end
  return ""
end

local function nodeText(node, sPath, sDefault)
  local s
  if type(node) == "string" then
    local sFullPath = node
    if sPath and sPath ~= "" then sFullPath = sFullPath .. "." .. sPath end
    s = DB.getText(sFullPath, sDefault or "")
  else
    s = DB.getText(node, sPath, sDefault or "")
  end
  if s == nil then return sDefault or "" end
  return tostring(s)
end

local function nodeNumber(node, sPath, nDefault)
  local value
  if type(node) == "string" then
    local sFullPath = node
    if sPath and sPath ~= "" then sFullPath = sFullPath .. "." .. sPath end
    value = DB.getValue(sFullPath, nDefault or 0)
  else
    value = DB.getValue(node, sPath, nDefault or 0)
  end
  return tonumber(value) or nDefault or 0
end

local function nodeToTable(node, nDepth)
  nDepth = nDepth or 0
  if nDepth > 12 then return { _truncated = true } end
  local sType = DB.getType(node)
  if sType == "number" then return tonumber(DB.getValue(node)) or 0 end
  if sType == "string" or sType == "formattedtext" then return DB.getText(node) or "" end
  if sType == "windowreference" then
    local sClass, sRecord = DB.getValue(node)
    return { class = sClass or "", record = sRecord or "" }
  end
  if sType ~= "node" then return DB.getText(node, "") or "" end
  local tResult = {}
  for sName, nodeChild in pairs(DB.getChildren(node)) do
    tResult[sName] = nodeToTable(nodeChild, nDepth + 1)
  end
  return tResult
end

local function sourceKey(node, sRecordType)
  return "5E:" .. sRecordType .. ":" .. DB.getPath(node)
end

local function moduleName(node)
  local sModule = DB.getModule(node) or ""
  if sModule == "" then return nil end
  return sModule
end

local function descriptionFor(node)
  local aPaths = { "description", "text", "summary", "desc", "features" }
  for _, sPath in ipairs(aPaths) do
    local sValue = nodeText(node, sPath, "")
    if sValue ~= "" then return sValue end
  end
  return ""
end

local function makeRecord(node, sRecordType)
  local sName = nodeText(node, "name", "")
  if sName == "" then sName = DB.getName(node) or "Unnamed" end
  return {
    source_key = sourceKey(node, sRecordType),
    record_type = sRecordType,
    name = sName,
    source_path = DB.getPath(node),
    module_name = moduleName(node) or JSON_NULL,
    fields = { description = descriptionFor(node) },
    raw = nodeToTable(node),
  }
end

local function mappingsFor(sRecordType)
  local aMappings = {}
  local tSeen = {}
  if LibraryData and LibraryData.getMappings then
    local ok, aRegistered = pcall(LibraryData.getMappings, sRecordType)
    if ok and type(aRegistered) == "table" then
      for _, sPath in ipairs(aRegistered) do
        if not tSeen[sPath] then table.insert(aMappings, sPath); tSeen[sPath] = true end
      end
    end
  end
  for _, sPath in ipairs(tFallbackMappings[sRecordType] or {}) do
    if not tSeen[sPath] then table.insert(aMappings, sPath); tSeen[sPath] = true end
  end
  return aMappings
end

local function recordsFor(sMappingType, sRecordType)
  local aRecords = {}
  local tSeen = {}
  for _, sPath in ipairs(mappingsFor(sMappingType)) do
    local ok, tNodes = pcall(DB.getChildrenGlobal, sPath)
    if ok and type(tNodes) == "table" then
      for _, node in pairs(tNodes) do
        local sPathKey = DB.getPath(node)
        if not tSeen[sPathKey] then
          local tRecord = makeRecord(node, sRecordType or sMappingType)
          if tRecord.name ~= "" then table.insert(aRecords, tRecord); tSeen[sPathKey] = true end
        end
      end
    end
  end
  table.sort(aRecords, function(a, b) return string.lower(a.name) < string.lower(b.name) end)
  return aRecords
end

local function classSummary(node)
  local aNames = {}
  local nTotal = 0
  for _, nodeClass in ipairs(DB.getChildList(node, "classes")) do
    local sName = nodeText(nodeClass, "name", "")
    local nLevel = nodeNumber(nodeClass, "level", 0)
    if sName ~= "" then table.insert(aNames, sName); nTotal = nTotal + nLevel end
  end
  if #aNames == 0 then
    local sName = nodeText(node, "class", "")
    if sName ~= "" then table.insert(aNames, sName) end
    nTotal = nodeNumber(node, "level", 1)
  end
  return table.concat(aNames, " / "), math.max(1, nTotal)
end

local function abilityScore(node, sAbility)
  return nodeNumber(node, "abilities." .. sAbility .. ".score", 10)
end

local function characterRecord(node)
  local sCharacterName = nodeText(node, "name", "")
  if sCharacterName == "" then return nil end
  local tRecord = makeRecord(node, "character")
  local sClass, nLevel = classSummary(node)
  local nMaximum = nodeNumber(node, "hp.total", nodeNumber(node, "hp.max", 1))
  local nWounds = nodeNumber(node, "hp.wounds", nodeNumber(node, "wounds", 0))
  local aFeats = {}
  for _, nodeFeat in ipairs(DB.getChildList(node, "featlist")) do
    local sName = nodeText(nodeFeat, "name", "")
    if sName ~= "" then table.insert(aFeats, sName) end
  end
  tRecord.fields = {
    player_name = DB.getOwner(node) or "",
    species = nodeText(node, "race", nodeText(node, "species", "")),
    class_name = sClass,
    subclass = nodeText(node, "specialization", ""),
    background = nodeText(node, "background", ""),
    level = nLevel,
    armor_class = nodeNumber(node, "defenses.ac.total", nodeNumber(node, "ac.totals.general", nodeNumber(node, "ac", 10))),
    max_hp = math.max(1, nMaximum),
    current_hp = math.max(0, nMaximum - nWounds),
    initiative_mod = nodeNumber(node, "initiative.total", nodeNumber(node, "initiative", 0)),
    abilities = {
      str = abilityScore(node, "strength"), dex = abilityScore(node, "dexterity"),
      con = abilityScore(node, "constitution"), int = abilityScore(node, "intelligence"),
      wis = abilityScore(node, "wisdom"), cha = abilityScore(node, "charisma"),
    },
    feats = table.concat(aFeats, "; "),
  }
  return tRecord
end

local function characters()
  local aRecords = {}
  for _, node in ipairs(DB.getChildList("charsheet")) do
    local tRecord = characterRecord(node)
    if tRecord then table.insert(aRecords, tRecord) end
  end
  table.sort(aRecords, function(a, b) return string.lower(a.name) < string.lower(b.name) end)
  return aRecords
end

local function encounterRecord(node)
  local tRecord = makeRecord(node, "encounter")
  tRecord.participants = {}
  local aPaths = { "npclist", "npcs", "combatants" }
  local tSeen = {}
  for _, sListPath in ipairs(aPaths) do
    for _, nodeParticipant in ipairs(DB.getChildList(node, sListPath)) do
      local sParticipantPath = DB.getPath(nodeParticipant)
      if not tSeen[sParticipantPath] then
        local sName = nodeText(nodeParticipant, "name", "Unnamed Participant")
        local nQuantity = math.max(1, nodeNumber(nodeParticipant, "count", nodeNumber(nodeParticipant, "number", 1)))
        local _, sLink = DB.getValue(nodeParticipant, "link")
        local nodeSource = nil
        if sLink and sLink ~= "" then nodeSource = DB.findNode(sLink) end
        nodeSource = nodeSource or nodeParticipant
        local sParticipantSourcePath = (sLink and sLink ~= "") and sLink or sParticipantPath
        table.insert(tRecord.participants, {
          source_key = "5E:npc:" .. sParticipantSourcePath,
          name = sName,
          quantity = nQuantity,
          armor_class = nodeNumber(nodeSource, "ac", nodeNumber(nodeParticipant, "ac", 10)),
          hit_points = math.max(1, nodeNumber(nodeSource, "hp", nodeNumber(nodeSource, "hp.total", nodeNumber(nodeParticipant, "hp", 1)))),
          initiative_mod = nodeNumber(nodeSource, "initiative", nodeNumber(nodeSource, "abilities.dexterity.bonus", 0)),
          raw = nodeToTable(nodeSource),
        })
        tSeen[sParticipantPath] = true
      end
    end
  end
  return tRecord
end

local function encounters()
  local aRecords = {}
  local tSeen = {}
  for _, sPath in ipairs(mappingsFor("battle")) do
    local ok, tNodes = pcall(DB.getChildrenGlobal, sPath)
    if ok and type(tNodes) == "table" then
      for _, node in pairs(tNodes) do
        local sPathKey = DB.getPath(node)
        -- Loaded modules expose hundreds of reference battles through global
        -- mappings. Only campaign-owned prepared encounters belong in this list.
        if not tSeen[sPathKey] and not moduleName(node) then
          table.insert(aRecords, encounterRecord(node)); tSeen[sPathKey] = true
        end
      end
    end
  end
  table.sort(aRecords, function(a, b) return string.lower(a.name) < string.lower(b.name) end)
  return aRecords
end

local function effectList(nodeCombatant)
  local aEffects = {}
  for _, nodeEffect in ipairs(DB.getChildList(nodeCombatant, "effects")) do
    table.insert(aEffects, {
      name = nodeText(nodeEffect, "label", nodeText(nodeEffect, "name", "Effect")),
      duration = nodeNumber(nodeEffect, "duration", 0),
      source = nodeText(nodeEffect, "source_name", nodeText(nodeEffect, "source", "")),
    })
  end
  return aEffects
end

local function combatState()
  local tCombat = {
    active = false, round = 0, active_source_key = JSON_NULL, combatants = {},
    session_key = sCombatSessionKey or JSON_NULL,
    session_name = sCombatSessionName or JSON_NULL,
    started_at = sSessionStartedAt or JSON_NULL,
    session_state = sSessionState,
    outcome = sOutcome or JSON_NULL,
    completed_at = sCompletedAt or JSON_NULL,
  }
  tCombat.round = nodeNumber("combattracker", "round", nodeNumber("combattracker", "roundcounter", 0))
  local aNodes = DB.getChildList("combattracker.list")
  table.sort(aNodes, function(a, b)
    local nA = nodeNumber(a, "initresult", 0)
    local nB = nodeNumber(b, "initresult", 0)
    if nA == nB then return DB.getPath(a) < DB.getPath(b) end
    return nA > nB
  end)
  for nIndex, node in ipairs(aNodes) do
    local nMaximum = nodeNumber(node, "hptotal", nodeNumber(node, "hp", 1))
    local nWounds = nodeNumber(node, "wounds", 0)
    local sKey = sourceKey(node, "ct")
    local tEntry = {
      source_key = sKey,
      name = nodeText(node, "name", "Unnamed Combatant"),
      order = nIndex - 1,
      initiative = nodeNumber(node, "initresult", 0),
      armor_class = nodeNumber(node, "ac", 10),
      hit_points = {
        maximum = math.max(1, nMaximum),
        current = math.max(0, nMaximum - nWounds),
        temporary = nodeNumber(node, "hptemp", 0),
        wounds = nWounds,
      },
      effects = effectList(node),
      raw = { source_path = DB.getPath(node), friendfoe = nodeText(node, "friendfoe", "") },
    }
    if nodeNumber(node, "active", 0) == 1 then tCombat.active_source_key = sKey end
    table.insert(tCombat.combatants, tEntry)
  end
  tCombat.active = #tCombat.combatants > 0
  return tCombat
end

local function loadedModules()
  local aLoaded = {}
  for _, sModule in ipairs(Module.getModules()) do
    local tInfo = Module.getModuleInfo(sModule)
    if tInfo and tInfo.loaded then table.insert(aLoaded, tInfo.displayname or sModule) end
  end
  table.sort(aLoaded)
  return aLoaded
end

local function campaignKey()
  local s = tostring(Session.CampaignName or "campaign")
  s = string.lower(s):gsub("[^%w%-_]+", "-"):gsub("^-+", ""):gsub("-+$", "")
  if s == "" then s = "campaign" end
  return s
end

local function ensureCombatSession(tCombat)
  tCombat.session_key = sCombatSessionKey or JSON_NULL
  tCombat.session_name = sCombatSessionName or JSON_NULL
  tCombat.started_at = sSessionStartedAt or JSON_NULL
  tCombat.session_state = sSessionState
  tCombat.outcome = sOutcome or JSON_NULL
  tCombat.completed_at = sCompletedAt or JSON_NULL
  return tCombat
end

local function eventParticipant(sSourceKey, sName)
  if not sName or sName == "" then return JSON_NULL end
  return { source_key = sSourceKey or JSON_NULL, name = sName }
end

local function combatantByKey(tCombat, sKey)
  if not sKey or sKey == JSON_NULL then return nil end
  for _, tEntry in ipairs(tCombat.combatants or {}) do
    if tEntry.source_key == sKey then return tEntry end
  end
  return nil
end

local function participantForCombatant(tEntry)
  if not tEntry then return JSON_NULL end
  return eventParticipant(tEntry.source_key, tEntry.name)
end

local function combatantForNode(node, tCombat)
  if not node then return nil end
  local sNodePath = DB.getPath(node) or ""
  for _, tEntry in ipairs(tCombat.combatants or {}) do
    local sCombatantPath = tEntry.raw and tEntry.raw.source_path or ""
    if sCombatantPath ~= "" and
      (sNodePath == sCombatantPath or sNodePath:sub(1, #sCombatantPath + 1) == sCombatantPath .. ".") then
      return tEntry
    end
  end
  return nil
end

local function combatantForActor(rActor, tCombat)
  if not rActor or not ActorManager then return nil end
  local node = nil
  if type(ActorManager.getCTNode) == "function" then node = ActorManager.getCTNode(rActor) end
  if not node and type(ActorManager.getCreatureNode) == "function" then node = ActorManager.getCreatureNode(rActor) end
  return combatantForNode(node, tCombat)
end

local function targetForCombatant(tEntry, tCombat)
  local sPath = tEntry and tEntry.raw and tEntry.raw.source_path or nil
  local nodeActor = sPath and DB.findNode(sPath) or nil
  if not nodeActor then return JSON_NULL, nil end
  for _, nodeTarget in ipairs(DB.getChildList(nodeActor, "targets")) do
    local sTargetPath = nodeText(nodeTarget, "noderef", "")
    local nodeTargetCombatant = sTargetPath ~= "" and DB.findNode(sTargetPath) or nil
    if nodeTargetCombatant then
      local sTargetKey = sourceKey(nodeTargetCombatant, "ct")
      local tTargetEntry = combatantByKey(tCombat, sTargetKey)
      if tTargetEntry then return participantForCombatant(tTargetEntry), tTargetEntry end
      return eventParticipant(sTargetKey, nodeText(nodeTargetCombatant, "name", "Target")), nil
    end
  end
  return JSON_NULL, nil
end

local function cleanRollDescription(sDescription)
  local s = tostring(sDescription or "")
  s = s:gsub("%[__ActionsManagerRoll__%]", " ")
  s = s:gsub("[\r\n]+", " ")
  s = s:gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  return s
end

local function rollActionName(sDescription)
  local s = cleanRollDescription(sDescription)
  s = s:gsub("%[[^%]]+%]", " ")
  s = s:gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  return s
end

local function contextForAppliedChange(tTarget, sKind)
  local tContext = tLastRollContext
  if not tContext or tContext.action_kind ~= sKind then return {} end
  if tContext.captured_at and tContext.captured_at > 0 and os and os.time and os.difftime then
    if os.difftime(os.time(), tContext.captured_at) > 10 then return {} end
  end
  local tExpected = tContext.target
  if tExpected and tExpected ~= JSON_NULL and tTarget and tTarget ~= JSON_NULL and
    tExpected.source_key ~= JSON_NULL and tTarget.source_key ~= JSON_NULL and
    tExpected.source_key ~= tTarget.source_key then
    return {}
  end
  return tContext
end

local function appendEvent(sType, tActor, tTarget, nAmount, sDescription, tMetadata, tCombat)
  if sSessionState ~= "open" or not sCombatSessionKey then
    if not bWarnedNoSession then
      chat("Combat event not recorded: run /lectern-start [encounter name] first.")
      bWarnedNoSession = true
    end
    return false
  end
  tCombat = ensureCombatSession(tCombat or combatState())
  nEventSequence = nEventSequence + 1
  local sSession = tCombat.session_key or "live-combat"
  table.insert(aEventJournal, {
    event_id = sSession .. ":" .. tostring(nEventSequence),
    sequence = nEventSequence,
    timestamp = isoTimestamp(),
    round = math.max(0, tonumber(tCombat.round) or 0),
    encounter_source_key = sSession,
    type = sType,
    actor = tActor or JSON_NULL,
    target = tTarget or JSON_NULL,
    amount = nAmount == nil and JSON_NULL or math.floor(tonumber(nAmount) or 0),
    description = sDescription or "",
    metadata = tMetadata or {},
  })
  while #aEventJournal > 1000 do table.remove(aEventJournal, 1) end
  if saveSessionState then pcall(saveSessionState) end
  return true
end

local function updateCombatBaseline(tCombat, bRecordEvents)
  local tCurrent = {}
  if bRecordEvents and bHaveCombatBaseline and sLastActiveKey ~= tCombat.active_source_key then
    tLastRollContext = nil
    if sLastActiveKey and sLastActiveKey ~= JSON_NULL then
      local tPrevious = tLastCombatants[sLastActiveKey]
      if tPrevious then appendEvent("turn_end", eventParticipant(tPrevious.source_key, tPrevious.name), nil, nil, "Turn ended", {}, tCombat) end
    end
    if tCombat.active_source_key and tCombat.active_source_key ~= JSON_NULL then
      for _, tEntry in ipairs(tCombat.combatants) do
        if tEntry.source_key == tCombat.active_source_key then
          appendEvent("turn_start", eventParticipant(tEntry.source_key, tEntry.name), nil, nil, "Turn started", {}, tCombat)
          break
        end
      end
    end
  end
  for _, tEntry in ipairs(tCombat.combatants) do
    local tHP = tEntry.hit_points or {}
    local nWounds = tonumber(tHP.wounds) or 0
    local nTemporary = tonumber(tHP.temporary) or 0
    local tPrevious = tLastCombatants[tEntry.source_key]
    if bRecordEvents and bHaveCombatBaseline and tPrevious then
      local nDelta = nWounds - tPrevious.wounds
      if nDelta > 0 then
        local tTarget = eventParticipant(tEntry.source_key, tEntry.name)
        local tContext = contextForAppliedChange(tTarget, "damage")
        local nRolled = tonumber(tContext.roll_total)
        local nAdjustment = nRolled and (nDelta - nRolled) or nil
        local bAttributed = tContext.actor and tContext.actor ~= JSON_NULL
        appendEvent("damage", tContext.actor, tTarget, nDelta,
          "Wounds increased from " .. tostring(tPrevious.wounds) .. " to " .. tostring(nWounds),
          { action_name = tContext.action_name or JSON_NULL, raw_roll = tContext.raw_roll or JSON_NULL,
            modifier = tContext.modifier or JSON_NULL, roll_total = tContext.roll_total or JSON_NULL,
            adjustment = nAdjustment or JSON_NULL, attribution = bAttributed and "matched_recent_roll" or "manual_or_unattributed",
            previous_wounds = tPrevious.wounds, current_wounds = nWounds,
            current_hp = tHP.current, maximum_hp = tHP.maximum }, tCombat)
        tLastRollContext = nil
      elseif nDelta < 0 then
        local tTarget = eventParticipant(tEntry.source_key, tEntry.name)
        local tContext = contextForAppliedChange(tTarget, "healing")
        appendEvent("healing", tContext.actor, tTarget, -nDelta,
          "Wounds decreased from " .. tostring(tPrevious.wounds) .. " to " .. tostring(nWounds),
          { action_name = tContext.action_name or JSON_NULL, raw_roll = tContext.raw_roll or JSON_NULL,
            modifier = tContext.modifier or JSON_NULL, roll_total = tContext.roll_total or JSON_NULL,
            previous_wounds = tPrevious.wounds, current_wounds = nWounds,
            current_hp = tHP.current, maximum_hp = tHP.maximum }, tCombat)
        tLastRollContext = nil
      end
      if nTemporary ~= tPrevious.temporary then
        appendEvent("effect", nil, eventParticipant(tEntry.source_key, tEntry.name), nil,
          "Temporary HP changed from " .. tostring(tPrevious.temporary) .. " to " .. tostring(nTemporary),
          { previous_temporary_hp = tPrevious.temporary, current_temporary_hp = nTemporary }, tCombat)
      end
    end
    tCurrent[tEntry.source_key] = { source_key = tEntry.source_key, name = tEntry.name, wounds = nWounds, temporary = nTemporary }
  end
  tLastCombatants = tCurrent
  sLastActiveKey = tCombat.active_source_key
  bLastCombatActive = tCombat.active
  bHaveCombatBaseline = true
end

local function handoffFolder()
  return File.getCampaignFolder() .. "/lectern-sync"
end

local function sessionStatePath()
  return handoffFolder() .. "/session-state.txt"
end

local function cleanStateLine(sValue)
  return tostring(sValue or ""):gsub("[\r\n]+", " ")
end

saveSessionState = function()
  local aLines = {
    cleanStateLine(sCombatSessionKey), cleanStateLine(sCombatSessionName),
    cleanStateLine(sSessionStartedAt), cleanStateLine(sSessionState),
    cleanStateLine(sOutcome), cleanStateLine(sCompletedAt), tostring(nEventSequence),
  }
  return File.saveTextFile(sessionStatePath(), table.concat(aLines, "\n"))
end

local function loadSessionState()
  local sSaved = File.openTextFile(sessionStatePath())
  if not sSaved or sSaved == "" then return end
  local aLines = {}
  for sLine in (sSaved .. "\n"):gmatch("([^\r\n]*)[\r\n]+") do table.insert(aLines, sLine) end
  local sState = aLines[4] or "inactive"
  if (sState ~= "open" and sState ~= "closed") or not aLines[1] or aLines[1] == "" then return end
  sCombatSessionKey = aLines[1]
  sCombatSessionName = aLines[2] ~= "" and aLines[2] or nil
  sSessionStartedAt = aLines[3] ~= "" and aLines[3] or nil
  sSessionState = sState
  sOutcome = aLines[5] ~= "" and aLines[5] or nil
  sCompletedAt = aLines[6] ~= "" and aLines[6] or nil
  nEventSequence = tonumber(aLines[7]) or 0
  local sSnapshot = File.openTextFile(handoffFolder() .. "/snapshot.json")
  sPersistedEventsJSON = extractArrayContents(sSnapshot or "", "events")
  nPersistedJournalCount = 0
end

local function initializeSequence()
  local sStatus = File.openTextFile(handoffFolder() .. "/status.json")
  if sStatus then nSequence = tonumber(sStatus:match('"sequence"%s*:%s*(%d+)')) or 0 end
end

local function writeStatus(sState, sMessage, sError)
  local tStatus = {
    extension_version = EXTENSION_VERSION,
    ruleset = tostring(Session.RulesetName or ""),
    campaign = tostring(Session.CampaignName or ""),
    sequence = nSequence,
    updated_at = isoTimestamp(),
    state = sState,
    message = sMessage or "",
    error = sError or "",
    combat_session_key = sCombatSessionKey or JSON_NULL,
    combat_session_name = sCombatSessionName or JSON_NULL,
    combat_session_state = sSessionState,
  }
  return File.saveTextFile(handoffFolder() .. "/status.json", encodeJSON(tStatus))
end

local function newSnapshot()
  local tCombat = ensureCombatSession(combatState())
  updateCombatBaseline(tCombat, false)
  return {
    schema_version = SCHEMA_VERSION,
    sequence = nSequence + 1,
    generated_at = isoTimestamp(),
    source = {
      provider = "fantasy_grounds",
      extension_version = EXTENSION_VERSION,
      ruleset = tostring(Session.RulesetName or ""),
      campaign_key = campaignKey(),
      campaign_name = tostring(Session.CampaignName or "Fantasy Grounds Campaign"),
      modules = loadedModules(),
    },
    catalog = {
      classes = recordsFor("class", "class"),
      subclasses = recordsFor("subclass", "subclass"),
      species = recordsFor("race", "species"),
      feats = recordsFor("feat", "feat"),
      backgrounds = recordsFor("background", "background"),
    },
    characters = characters(),
    encounters = encounters(),
    combat = tCombat,
    events = aEventJournal,
  }
end

local function saveSnapshot(tSnapshot)
  tSnapshot.sequence = nSequence + 1
  tSnapshot.generated_at = isoTimestamp()
  local aNewEvents = {}
  for nIndex = nPersistedJournalCount + 1, #aEventJournal do
    table.insert(aNewEvents, encodeJSON(aEventJournal[nIndex]))
  end
  local sMergedEvents = sPersistedEventsJSON
  if #aNewEvents > 0 then
    if sMergedEvents ~= "" then sMergedEvents = sMergedEvents .. "," end
    sMergedEvents = sMergedEvents .. table.concat(aNewEvents, ",")
  end
  local aSnapshotEvents = tSnapshot.events
  tSnapshot.events = {}
  local sJSON = encodeJSON(tSnapshot)
  tSnapshot.events = aSnapshotEvents
  sJSON = sJSON:gsub('"events":%[%]', function() return '"events":[' .. sMergedEvents .. ']' end, 1)
  local sSnapshotPath = handoffFolder() .. "/snapshot.json"
  File.saveTextFile(sSnapshotPath, sJSON)
  local sWritten = File.openTextFile(sSnapshotPath)
  if not sWritten or #sWritten == 0 then
    error("Snapshot file could not be read after writing; create the lectern-sync folder from Lectern first")
  end
  nSequence = tSnapshot.sequence
  sPersistedEventsJSON = sMergedEvents
  nPersistedJournalCount = #aEventJournal
  writeStatus("ready", "Snapshot exported", "")
end

function exportAll()
  if bExporting then return end
  if not Session.IsHost then chat("Export is available only to the campaign host."); return end
  if tostring(Session.RulesetName or "") ~= "5E" then chat("Lectern Sync 1.0 supports only the 5E ruleset."); return end
  bExporting = true
  local ok, result = pcall(function()
    writeStatus("exporting", "Reading Fantasy Grounds records", "")
    local snapshot = newSnapshot()
    saveSnapshot(snapshot)
    tCachedSnapshot = snapshot
    return snapshot
  end)
  bExporting = false
  if ok then
    chat("Exported sequence " .. tostring(nSequence) .. " to " .. handoffFolder())
  else
    pcall(writeStatus, "error", "Export failed", tostring(result))
    chat("Export failed: " .. tostring(result) .. ". Ensure Lectern created the campaign's lectern-sync folder.")
  end
end

local function exportCombatUpdate()
  if bExporting or not tCachedSnapshot or not Session.IsHost then return end
  bExporting = true
  local ok, result = pcall(function()
    local tCombat = ensureCombatSession(combatState())
    updateCombatBaseline(tCombat, true)
    tCachedSnapshot.combat = tCombat
    tCachedSnapshot.events = aEventJournal
    saveSnapshot(tCachedSnapshot)
  end)
  bExporting = false
  if not ok then pcall(writeStatus, "error", "Combat export failed", tostring(result)) end
end

local function diceValue(draginfo, sMethod, vDefault)
  if not draginfo or type(draginfo[sMethod]) ~= "function" then return vDefault end
  local ok, value = pcall(draginfo[sMethod])
  if ok and value ~= nil then return value end
  return vDefault
end

local function classifyRoll(sRollType, sDescription)
  local s = string.lower(tostring(sRollType or "") .. " " .. tostring(sDescription or ""))
  if s:find("attack", 1, true) then return "attack" end
  if s:find("damage", 1, true) or s:find("heal", 1, true) then return "action" end
  if s:find("save", 1, true) then return "save" end
  if s:find("spell", 1, true) or s:find("cast", 1, true) then return "spell" end
  return "action"
end

local function authoritativeAttackResolved(rSource, rTarget, rRoll)
  if not Session.IsHost or not rRoll then return end
  local tCombat = combatState()
  local tActorEntry = combatantForActor(rSource, tCombat)
  local tTargetEntry = combatantForActor(rTarget, tCombat)
  local tActor = participantForCombatant(tActorEntry)
  local tTarget = participantForCombatant(tTargetEntry)
  local nRawRoll = tonumber(rRoll.nFirstDie)
  local nTotal = tonumber(rRoll.nTotal)
  local nModifier = nRawRoll and nTotal and (nTotal - nRawRoll) or tonumber(rRoll.nMod) or 0
  local nTargetAC = tonumber(rRoll.nDefenseVal)
  local tResults = {
    crit = "Critical Hit", fumble = "Automatic Miss", hit = "Hit", miss = "Miss",
  }
  local sResult = tResults[tostring(rRoll.sResult or "")] or "Result not reported"
  local sActionName = rollActionName(rRoll.sDesc or "Attack")
  tLastRollContext = {
    actor = tActor, target = tTarget, action_name = sActionName, action_kind = "attack",
    raw_roll = nRawRoll or JSON_NULL, modifier = nModifier,
    roll_total = nTotal or JSON_NULL, result = sResult,
    captured_at = os and os.time and os.time() or 0,
  }
  appendEvent("attack", tActor, tTarget, nil, cleanRollDescription(rRoll.sDesc or "Attack"), {
    action_name = sActionName, roll_type = "attack", raw_roll = nRawRoll or JSON_NULL,
    modifier = nModifier, roll_total = nTotal or JSON_NULL, target_ac = nTargetAC or JSON_NULL,
    attack_effect_bonus = tonumber(rRoll.nAtkEffectsBonus) or 0,
    defense_effect_bonus = tonumber(rRoll.nDefEffectsBonus) or 0,
    natural_roll = nRawRoll or JSON_NULL, result = sResult, authoritative_result = true,
  }, tCombat)
  exportCombatUpdate()
end

local function onDiceLanded(draginfo)
  if not Session.IsHost then return end
  local sRollType = tostring(diceValue(draginfo, "getType", "roll") or "roll")
  local sDescription = cleanRollDescription(diceValue(draginfo, "getDescription", sRollType) or sRollType)
  local tDice = diceValue(draginfo, "getDiceData", {})
  local nRawRoll = type(tDice) == "table" and tonumber(tDice.total) or nil
  local nModifier = tonumber(diceValue(draginfo, "getNumberData", 0)) or 0
  local nTotal = nRawRoll and (nRawRoll + nModifier) or nil
  local tCombat = combatState()
  local node = diceValue(draginfo, "getDatabaseNode", nil)
  local tActorCombatant = combatantForNode(node, tCombat) or combatantByKey(tCombat, tCombat.active_source_key)
  local tActor = participantForCombatant(tActorCombatant)
  local tTarget, tTargetCombatant = targetForCombatant(tActorCombatant, tCombat)
  local sActionName = rollActionName(sDescription)
  local sResult = JSON_NULL
  local sLower = string.lower(sDescription)
  if sLower:find("[hit]", 1, true) then sResult = "Hit"
  elseif sLower:find("[miss]", 1, true) then sResult = "Miss" end
  local sEventType = classifyRoll(sRollType, sDescription)
  if sEventType == "attack" and bHaveAuthoritativeAttackHook then return end
  local nTargetAC = tTargetCombatant and tonumber(tTargetCombatant.armor_class) or nil
  if sEventType == "attack" and sResult == JSON_NULL and nTotal and nTargetAC then
    sResult = nTotal >= nTargetAC and "Hit" or "Miss"
  end
  tLastRollContext = {
    actor = tActor, target = tTarget, action_name = sActionName,
    action_kind = sLower:find("damage", 1, true) and "damage" or
      (sLower:find("heal", 1, true) and "healing" or sEventType),
    raw_roll = nRawRoll or JSON_NULL, modifier = nModifier,
    roll_total = nTotal or JSON_NULL, result = sResult,
    captured_at = os and os.time and os.time() or 0,
  }
  appendEvent(sEventType, tActor, tTarget, nil, sDescription,
    { action_name = sActionName, roll_type = sRollType,
      raw_roll = nRawRoll or JSON_NULL, modifier = nModifier,
      roll_total = nTotal or JSON_NULL, target_ac = nTargetAC or JSON_NULL,
      result = sResult }, tCombat)
  exportCombatUpdate()
end

local function startEncounter(_, sParameters)
  if not Session.IsHost then return end
  if sSessionState == "open" and sCombatSessionKey then
    chat("An encounter is already open: " .. tostring(sCombatSessionName or sCombatSessionKey) .. ". Run /lectern-end outcome first.")
    return
  end
  local sName = tostring(sParameters or ""):gsub("^%s+", ""):gsub("%s+$", "")
  local sStarted = isoTimestamp()
  if sName == "" then sName = "Fantasy Grounds Combat " .. sStarted:sub(1, 10) end
  local sStamp = sStarted:gsub("[^%w]", "")
  sCombatSessionKey = "combat-" .. campaignKey() .. "-" .. sStamp .. "-" .. tostring(nSequence + 1)
  sCombatSessionName = sName
  sSessionStartedAt = sStarted
  sSessionState = "open"
  sOutcome = nil
  sCompletedAt = nil
  nEventSequence = 0
  aEventJournal = {}
  nPersistedJournalCount = 0
  tLastCombatants = {}
  sLastActiveKey = nil
  bHaveCombatBaseline = false
  bLastCombatActive = false
  tLastRollContext = nil
  bWarnedNoSession = false
  local tCombat = ensureCombatSession(combatState())
  updateCombatBaseline(tCombat, false)
  appendEvent("action", nil, nil, nil, "Encounter started: " .. sName,
    { lifecycle = "encounter_start", session_name = sName, started_at = sStarted }, tCombat)
  pcall(saveSessionState)
  if tCachedSnapshot then exportCombatUpdate() else exportAll() end
  chat("Started Lectern encounter: " .. sName)
end

local function endEncounter(_, sParameters)
  if not Session.IsHost then return end
  local sValue = string.lower(tostring(sParameters or "")):match("^%s*(%S+)") or ""
  local tAllowed = { victory = true, defeat = true, retreat = true, unresolved = true }
  if not tAllowed[sValue] then
    chat("Usage: /lectern-end victory|defeat|retreat|unresolved")
    return
  end
  if sSessionState ~= "open" or not sCombatSessionKey then
    chat("No Lectern encounter is open. Run /lectern-start [encounter name] first.")
    return
  end
  local tCombat = ensureCombatSession(combatState())
  sOutcome = sValue
  sCompletedAt = isoTimestamp()
  tCombat.outcome = sOutcome
  tCombat.completed_at = sCompletedAt
  appendEvent("outcome", nil, nil, nil, "Encounter ended: " .. sValue,
    { lifecycle = "encounter_end", outcome = sValue, completed_at = sCompletedAt }, tCombat)
  sSessionState = "closed"
  pcall(saveSessionState)
  if tCachedSnapshot then exportCombatUpdate() else exportAll() end
  chat("Ended Lectern encounter " .. tostring(sCombatSessionName or sCombatSessionKey) .. ": " .. sValue)
end

local function setOutcome(_, sParameters)
  endEncounter(nil, sParameters)
end

local function resetEncounterJournal(_, sParameters)
  if not Session.IsHost then return end
  if tostring(sParameters or ""):lower():match("^%s*(.-)%s*$") ~= "confirm" then
    chat("Usage: /lectern-reset confirm (clears the closed Lectern session and exported event journal)")
    return
  end
  if sSessionState == "open" and sCombatSessionKey then
    chat("The Lectern encounter is still open. Run /lectern-end outcome before resetting.")
    return
  end
  sCombatSessionKey = nil
  sCombatSessionName = nil
  sSessionStartedAt = nil
  sSessionState = "inactive"
  sOutcome = nil
  sCompletedAt = nil
  nEventSequence = 0
  aEventJournal = {}
  sPersistedEventsJSON = ""
  nPersistedJournalCount = 0
  tLastCombatants = {}
  sLastActiveKey = nil
  bHaveCombatBaseline = false
  bLastCombatActive = false
  tLastRollContext = nil
  bWarnedNoSession = false
  tCachedSnapshot = nil
  pcall(saveSessionState)
  exportAll()
  chat("Cleared the Lectern combat session and exported event journal. Start the next test with /lectern-start [name].")
end

local function onCombatTrackerChanged()
  exportCombatUpdate()
end

local function onModuleChanged()
  tCachedSnapshot = nil
  pcall(writeStatus, "stale", "Module set changed; run /lectern-export", "")
end

function onInit()
  if not Session.IsHost then return end
  initializeSequence()
  loadSessionState()
  Comm.registerSlashHandler("lectern-export", exportAll, "Export 5E catalog, campaign, encounters, and combat to Lectern")
  Comm.registerSlashHandler("lectern-start", startEncounter, "Start and name a durable Lectern combat encounter")
  Comm.registerSlashHandler("lectern-end", endEncounter, "End the current Lectern encounter with an outcome")
  Comm.registerSlashHandler("lectern-reset", resetEncounterJournal, "Clear a closed Lectern combat session and event journal")
  Comm.registerSlashHandler("lectern-outcome", setOutcome, "Compatibility alias for /lectern-end")
  Comm.addKeyedEventHandler("onDiceLanded", "", onDiceLanded)
  if GameManager and type(GameManager.addEventFunction) == "function" then
    GameManager.addEventFunction("onAttackPostResolve", authoritativeAttackResolved)
    bHaveAuthoritativeAttackHook = true
  end
  DB.addHandler("combattracker.list.*.wounds", "onUpdate", onCombatTrackerChanged)
  DB.addHandler("combattracker.list.*.hptemp", "onUpdate", onCombatTrackerChanged)
  DB.addHandler("combattracker.list.*.active", "onUpdate", onCombatTrackerChanged)
  DB.addHandler("combattracker.round", "onUpdate", onCombatTrackerChanged)
  DB.addHandler("combattracker.list", "onChildAdded", onCombatTrackerChanged)
  DB.addHandler("combattracker.list", "onChildDeleted", onCombatTrackerChanged)
  Module.addEventHandler("onModuleLoad", onModuleChanged)
  Module.addEventHandler("onModuleUnload", onModuleChanged)
  local sReadyMessage = "Run /lectern-export to create the first snapshot"
  if sSessionState == "open" then
    sReadyMessage = "Resumed open encounter: " .. tostring(sCombatSessionName or sCombatSessionKey)
  end
  pcall(writeStatus, "waiting", sReadyMessage, "")
  chat("Ready. Run /lectern-start [name] before combat and /lectern-end outcome when it finishes.")
end

function onClose()
  if not Session.IsHost then return end
  pcall(saveSessionState)
  if bHaveAuthoritativeAttackHook and GameManager and type(GameManager.removeEventFunction) == "function" then
    GameManager.removeEventFunction("onAttackPostResolve", authoritativeAttackResolved)
  end
  DB.removeHandler("combattracker.list.*.wounds", "onUpdate", onCombatTrackerChanged)
  DB.removeHandler("combattracker.list.*.hptemp", "onUpdate", onCombatTrackerChanged)
  DB.removeHandler("combattracker.list.*.active", "onUpdate", onCombatTrackerChanged)
  DB.removeHandler("combattracker.round", "onUpdate", onCombatTrackerChanged)
  DB.removeHandler("combattracker.list", "onChildAdded", onCombatTrackerChanged)
  DB.removeHandler("combattracker.list", "onChildDeleted", onCombatTrackerChanged)
  Module.removeEventHandler("onModuleLoad", onModuleChanged)
  Module.removeEventHandler("onModuleUnload", onModuleChanged)
  Comm.removeKeyedEventHandler("onDiceLanded", "", onDiceLanded)
end
