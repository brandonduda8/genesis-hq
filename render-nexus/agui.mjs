/**
 * Pure, read-only AG-UI event preview for an already SHA-256-validated
 * GitHub A2A mailbox record. It does not authorize, execute, send, spend or
 * prove which human/agent committed a record.
 */
const IDENT=/^[A-Za-z0-9_-]{1,64}$/;
const MID=/^msg-[a-f0-9]{32}$/;
const STATES=new Map([
  ['submitted','STAGED'],
  ['working','SELF_REPORTED_WORKING'],
  ['completed','REVIEW_REQUIRED'],
  ['failed','SELF_REPORTED_FAILED'],
  ['canceled','SELF_REPORTED_CANCELED'],
  ['input-required','SELF_REPORTED_INPUT_REQUIRED'],
  ['auth-required','SELF_REPORTED_AUTH_REQUIRED'],
  ['rejected','SELF_REPORTED_REJECTED'],
]);
const invalid=why=>{const err=new Error('Not displayable: '+why);err.status=422;throw err;};

export function aguiPreview(record, now=new Date()){
  if(!(now instanceof Date)||!Number.isFinite(now.getTime())) invalid('invalid evaluation time');
  if(!record||typeof record!=='object'||Array.isArray(record)||record.transport!=='RECORDED_IN_GITHUB'||record.execution!=='NOT_VERIFIED')
    invalid('unsupported record trust level');
  if(typeof record.message_id!=='string'||!MID.test(record.message_id)
    ||typeof record.route!=='string'||!/^([a-z]+)-to-([a-z]+)$/.test(record.route))
    invalid('invalid source identity');
  if(typeof record.conversation_id!=='string'||!IDENT.test(record.conversation_id)
    ||typeof record.content!=='string'||Buffer.byteLength(record.content,'utf8')>262144)
    invalid('invalid content or context');
  if(typeof record.created_at!=='string'||Number.isNaN(Date.parse(record.created_at)))
    invalid('invalid creation timestamp');
  if(record.expires_at!==null&&record.expires_at!==undefined
    &&(typeof record.expires_at!=='string'||Number.isNaN(Date.parse(record.expires_at))
      ||Date.parse(record.expires_at)<=now.getTime())) invalid('expired message');

  let task;
  try{task=JSON.parse(record.content)}catch{invalid('not a JSON task');}
  if(!task||typeof task!=='object'||Array.isArray(task)||task.kind!=='task'
    ||typeof task.taskId!=='string'||!IDENT.test(task.taskId)
    ||task.contextId!==record.conversation_id
    ||!task.status||typeof task.status!=='object'
    ||!STATES.has(task.status.state)) invalid('unsupported A2A task');
  const claimedWorker=record.route.split('-to-')[0];
  const state={
    task_id:task.taskId,
    mission_id:task.contextId,
    message_id:record.message_id,
    reported_by:claimedWorker,
    claimed_remote_state:task.status.state,
    phoenix_display_state:STATES.get(task.status.state),
    observed_source:'GITHUB_MAILBOX_DIGEST_VALID',
    peer_identity:'UNVERIFIED',
    worker_liveness:'UNKNOWN',
    independent_review:'NOT_VERIFIED',
    approved_action:false,
    remote_execution_verified:false,
    verified_revenue_usd:null,
    claimed_message_at:record.created_at,
    is_display_only:true,
  };
  const runId='display-'+record.message_id;
  return {
    mode:'READ_ONLY_AGUI_EVENT_PREVIEW',
    execution:'NOT_VERIFIED',
    caveat:'Event objects only; not a streaming AG-UI worker endpoint or full OpenDots deployment.',
    events:[
      {type:'RUN_STARTED',threadId:task.contextId,runId},
      {type:'STATE_SNAPSHOT',snapshot:{genesis:state}},
      {type:'RUN_FINISHED',threadId:task.contextId,runId,result:'DISPLAY_PREVIEW_FINISHED_NOT_REMOTE_TASK'},
    ],
  };
}
