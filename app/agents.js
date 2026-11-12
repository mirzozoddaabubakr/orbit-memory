const repository='https://github.com/mirzozoddaabubakr/orbit-memory';
export function skillSection(icon){
  return '<section class="skill-section"><div class="section-head"><h2>Agent skills</h2><a class="text-btn" href="'+repository+'/tree/main/skills" target="_blank" rel="noopener noreferrer">GitHub '+icon('diagonal',15)+'</a></div>'+
    '<p>Connect MCP first, then install a skill in your agent.</p><div class="skill-cards">'+[
      ['orbit-memory','Remember & recall','Save conversations and find earlier work.'],
      ['orbit-handoff','Project handoff','Carry decisions and progress to another AI.']
    ].map(([id,title,description])=>'<article class="skill-card"><h3>'+title+'</h3><p>'+description+'</p><div><a class="plain" href="/api/skills/'+id+'" download="SKILL.md">Download skill</a><a class="text-btn" href="'+repository+'/blob/main/skills/'+id+'/SKILL.md" target="_blank" rel="noopener noreferrer">View on GitHub '+icon('diagonal',14)+'</a></div></article>').join('')+'</div></section>';
}
