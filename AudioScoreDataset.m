classdef AudioScoreDataset < handle
    % A class to represent data, load them, split etc.
    properties
        data    % the output of `jsondecode`: a structured array representing the dataset
        paths   % an cell-array containing the paths of the filtered songs
                % [mixed paths, sources paths, ground_truth paths]
        decompress_path
        install_dir % a string representing the path where the dataset is installed
    end
    
    methods
        function obj = AudioScoreDataset(path)
            % Create a class instance by loading the json file specified in `path`
            obj.data = jsondecode(fileread(path));
            obj.set_install_dir(obj.data.install_dir);
            obj.decompress_path = './';
        end

        function set_install_dir(obj, dir)
            % set the `install_dir` field of this object and add it to the path
            obj.install_dir = dir;
            addpath(dir);
        end

        function filter(obj, varargin)
            % Filter the dataset according to the parameters:
            % - `instrument`:   a string representing the instrument that you
            %                   want to select (only one supported for now)
            % - `ensemble`:     if loading songs which are composed for an ensemble of
            %                   instrument (default `false`)
            % - `mixed`:        if returning the mixed track for ensemble song
            %                   (default `true`)
            % - `sources`:      if returning the source track for ensemble recording
            %                   which provide it (default `false`)
            % - `all`:          only valid if `sources` is `true`: if `true`, all
            %                   sources (audio and ground-truth) are returned, if
            %                   `false`, only the target instrument is
            %                   returned. Default `false`.
            % - `composer`:     the surname of the composer to filter
            % - `datasets`:     a list of strings containing the name of the
            %                   datasets to be used. If empty, all datasets are used.
            % - `ground_truth`: a list of strings representing the type of
            %                   ground-truths needed (logical AND among list elements)
            %
            % All parameters are optional and in name-value syntax

            % starting parser
            p = inputParser;
            addParameter(p, 'ensemble', false);
            addParameter(p, 'mixed', true);
            addParameter(p, 'sources', false);
            addParameter(p, 'all', false);
            addParameter(p, 'composer', -1);
            addParameter(p, 'instrument', -1);
            addParameter(p, 'datasets', []);
            addParameter(p, 'ground_truth', []);
            parse(p, varargin{:});

            for i = 1:length(obj.data.datasets)
                mydataset = obj.data.datasets{i};

                FLAG = true;
                if length(p.Results.datasets) > 0
                    FLAG = false;
                    for i = 1:length(p.Results.datasets)
                        dataset = p.Results.datasets{i};
                        if strcmp(mydataset.name, dataset)
                            FLAG = true;
                            break;
                        end
                    end
                end

                % checking dataset-level filters
                if p.Results.ensemble ~= mydataset.ensemble
                    FLAG = false;
                end

                if p.Results.instrument ~= -1
                    if ~contains(mydataset.instruments, p.Results.instrument)
                        FLAG = false;
                    end
                end

                for i = 1:length(p.Results.ground_truth)
                    gt = p.Results.ground_truth{i};
                    if getfield(mydataset.ground_truth, gt{1}) ~= gt{2}
                        FLAG = false;
                        break;
                    end
                end

                if FLAG
                    for k = 1:length(mydataset.songs)
                        song = mydataset.songs(k);
                        % checking song levels filters
                        if p.Results.instrument ~= -1
                            if ~contains(song.instruments, p.Results.instrument)
                                FLAG = false;
                            end
                        end

                        if p.Results.composer ~= -1
                            if ~strcmp(p.Results.composer, song.composer)
                                FLAG = false;
                            end
                        end

                        if FLAG
                            gts = {song.ground_truth};
                            sources = {''};
                            mixed = {''};
                            if p.Results.sources & getfield(song, "sources")
                                if p.Results.all 
                                    sources = {song.sources.path};
                                else
                                    % find the index of the instrument
                                    idx = find(contains(song.instruments, p.Results.instrument));

                                    % take index of the target instrument
                                    sources = {song.sources.path(idx)};
                                    gts = {song.ground_truth(idx)};
                                end
                            end

                            if p.Results.mixed
                                mixed = {song.recording.path};
                            end
                            obj.paths = [obj.paths; mixed sources gts];
                        end % closing `if FLAG` check

                    end % closing song loop
                end % closing `if FLAG` check
            end % closing dataset loop
        end % closing method

        function move_to_ram(obj, tmpfs)
            % - `tmpfs`: a string representing the directory where the returned
            %            ground truth files are copied. In linux, it is
            %            recommended to use a tmpfs filesystem.  If free space
            %            is enough, than all ground-truth files are
            %            moved there, so that every compressed file is already
            %            in RAM. Also, every file will be decompressed in this
            %            path.
            %
            %            I recommend to do not use this parameter if not in
            %            linux.
            %
            %            Note that all the ground-truth files need at least XX
            %            GB of RAM, but if you filter them, you'll need less
            %            space.
            for i = 1:length(obj.paths)
                for j = 1:length(obj.paths{i, 3})
                    filepath = obj.paths{i, 3}{j};
                    if ~movefile(filepath, tmpfs)
                        fprintf('Cannot move %s\n', filepath);
                        return;
                    end
                    filepath, filename, ext = fileparts(obj.paths{i, 3}{j});
                    obj.paths{i, 3}{j} = {strcat(filename, ext)};
                end
            end

            obj.set_install_dir(tmpfs);
            obj.set_decompress_path(tmpfs);
        end

        function set_decompress_path(obj, tmpfs)
            % - `tmpfs`: a string representing the directory where the returned
            %            ground truth files are decompressed. In linux, it is
            %            Suggested at least 512 MB or free space.
            %
            %            I recommend to do not use this parameter if not in
            %            linux. Even in linux, slight improvements are actually achieved.
            obj.decompress_path = tmpfs;
        end

        function [mix, sr] = get_mix(obj, idx)
            % - `idx`: the index of the wanted item.
            %
            % RETURNED:
            % - `mix`:      the audio waveform of the mixed song (array) mixed to mono
            % - `sr`:       the sampling rate
            %
            recordings_fn = obj.paths{idx, 1};

            recordings = [];
            if length(recordings_fn) > 1
                for k = 1:length(recordings_fn)
                    [rec, sr] = audioread(fullfile(obj.install_dir, recordings_fn{k}));
                    recordings = [recordings; rec];
                end

                mix = {mean(recordings, 2)};
            else
                [mix, sr] = audioread(fullfile(obj.install_dir, recordings_fn{1}));
                mix = {mean(mix, 2)};
            end
        end

        function gts = get_gts(obj, idx)
            % - `idx`: the index of the wanted item.
            %
            % RETURNED:
            % - `gts`:  the ground-truths of each single source (1xn struct array with fields)
            %
            gts_fn = obj.paths{idx, 3};
            for k = 1:length(gts_fn)

                [filepath,name,ext] = fileparts(gts_fn{k});
                input_fn = fullfile(obj.install_dir, gts_fn{k});
                output_fn = fullfile(obj.decompress_path, name);

                gunzip(input_fn, obj.decompress_path);
                gts(k) = jsondecode(fileread(output_fn));
                delete(output_fn);
            end
        end

        function [sources, sr] = get_source(obj, idx)
            % - `idx`: the index of the wanted item.
            %
            % RETURNED:
            % - `sources`:  the audio values of each sources (nx1 cell-array)
            % - `sr`:   the sampling rate
            %
            sources_fn = obj.paths{idx, 2};

            for k = 1:length(sources_fn)
                [sources{k}, sr] = audioread(fullfile(obj.install_dir, sources_fn{k}));
            end

        end

        function [mix, sources, gts] = get_item(obj, idx)
            % - `idx`: the index of the wanted item.
            %
            % RETURNED:
            % - `mix`:      the audio waveform of the mixed song (array)
            % - `sources`:  the audio values of each sources (nx1 cell-array)
            % - `gts`:      the ground-truths of each single source (1xn struct array with fields)
            %
            mix = obj.get_mix(idx);
            sources = obj.get_source(idx);
            gts = obj.get_gts(idx);
        end

        function mat_score = get_score(obj, idx, mat_score_type)
            % - `idx`: the index of the wanted item.
            % - `mat_score_type`: a string indicating the type of the mat_score
            %
            % RETURNED:
            % - `mat_score`: the ground-truth of all the instruments (struct array
            % with fields)
            mat_score = [];
            disp('    Loading ground truth');
            gts = obj.get_gts(idx);
            for i = 1:length(gts)
                gt = gts(1, i);
                % This is due to Bach10 datasets
                diff_notes = 0;
                find_bach10_errors(gt, mat_score_type);
                gt = truncate_score(gt);

                % initialize each column
                score_type_ = getfield(gt, mat_score_type);
                ons = score_type_.onsets;
                if length(ons) == 0
                    ons = repmat(-255, length(gt.pitches), 1);
                end

                offs = score_type_.offsets;
                if length(offs) == 0
                    offs = repmat(-255, length(gt.pitches), 1);
                end

                vel = gt.velocities;
                if length(vel) == 0
                    vel = repmat(-255, length(gt.pitches), 1);
                end

                num = repmat(i, length(gt.pitches), 1);
                instr = repmat(gt.instrument, length(gt.pitches), 1);

                try
                    mat_score = [mat_score; gt.pitches ons offs vel instr num];
                catch
                    keyboard
                end

            end
            % sorting by onset
            mat_score = sortrows(mat_score, 2);
        end

    end % closing method section
end % closing class

function find_bach10_errors(gt, score_type)
    if length(gt.pitches) ~= length(gt.non_aligned.onsets)
        end_idx = length(gt.pitches) - length(gt.non_aligned.onsets);
        disp('---- This file contains different data in non-aligned and number of pitches!');
        fprintf('---- %d different notes\n', end_idx);
    end
end

function gt = truncate_score(gt)
    score_types = [ "non_aligned", "precise_alignment", "broad_alignment" ];

    % looking for the length of the final lists
    len = length(gt.pitches);
    for score_type = score_types
        score_type_ = getfield(gt, score_type);
        onsets_len = length(score_type_.onsets);
        if onsets_len > 0
            len = min(len, onsets_len);
        end
    end
    
    % truncating lists
    if length(gt.velocities) > 0
        len = min(len, length(gt.velocities));
        gt.velocities = gt.velocities(1:len);
    end

    gt.pitches = gt.pitches(1:len);
    for score_type = score_types
        if length(gt.(score_type).onsets) > 0
            gt.(score_type).onsets = gt.(score_type).onsets(1:len);
            gt.(score_type).offsets = gt.(score_type).offsets(1:len);
        end
    end
end
