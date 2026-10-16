# runs/

One folder per run, named by run ID (`R-0001`, `R-0002`, ...), created by the agent before the run starts:

    runs/R-0001/
      run.md          what, why, exact command, git commit, start/end time, machine, outcome (filled in after)
      config.yaml     every setting used (model, data, learning rate, steps, seed)
      metrics.json    final WER/CER and per-checkpoint scores
      train.log       full console log (if > 5 MB, keep it in S3 and put the S3 path in run.md)
      samples.md      20 test clips: reference text vs model output (shows the kinds of mistakes)
      loss.png        training/validation loss curve

Failed or cancelled runs keep their folder too; mark them in run.md and results.md.
Model checkpoints are never stored here (too big): they live in S3, and run.md records the path.
